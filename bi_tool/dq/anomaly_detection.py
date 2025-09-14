"""
Data Quality Anomaly Detection System
Statistical and ML-based anomaly detection for time-series data quality metrics.
"""

import logging
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Any, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
from django.utils import timezone
from django.db.models import Q
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler
from scipy import stats
from scipy.signal import find_peaks

from .models import DQRule, DQRun, DQMetric, DQAnomalyDetection, DQRunStatus

logger = logging.getLogger(__name__)


class AnomalyMethod(Enum):
    """Anomaly detection methods."""
    STATISTICAL = "statistical"
    ISOLATION_FOREST = "isolation_forest"
    Z_SCORE = "z_score"
    IQR = "iqr"
    SEASONAL_DECOMPOSITION = "seasonal_decomposition"
    CHANGE_POINT = "change_point"


@dataclass
class AnomalyResult:
    """Result of anomaly detection."""
    is_anomaly: bool
    confidence: float
    method: str
    threshold_value: float
    actual_value: float
    expected_range: Tuple[float, float]
    context: Dict[str, Any]


class DQAnomalyDetector:
    """Main anomaly detection class for data quality metrics."""
    
    def __init__(self):
        self.methods = {
            AnomalyMethod.STATISTICAL.value: self._detect_statistical_anomaly,
            AnomalyMethod.ISOLATION_FOREST.value: self._detect_isolation_forest_anomaly,
            AnomalyMethod.Z_SCORE.value: self._detect_zscore_anomaly,
            AnomalyMethod.IQR.value: self._detect_iqr_anomaly,
            AnomalyMethod.SEASONAL_DECOMPOSITION.value: self._detect_seasonal_anomaly,
            AnomalyMethod.CHANGE_POINT.value: self._detect_change_point_anomaly,
        }
        self.default_lookback_days = 30
        self.default_min_samples = 10
    
    def detect_anomalies(
        self,
        rule_id: int,
        method: str = "statistical",
        lookback_days: int = None,
        sensitivity: float = 0.05
    ) -> List[AnomalyResult]:
        """Detect anomalies for a specific DQ rule."""
        lookback_days = lookback_days or self.default_lookback_days
        
        try:
            # Get historical data
            historical_data = self._get_historical_data(rule_id, lookback_days)
            
            if len(historical_data) < self.default_min_samples:
                logger.warning(f"Insufficient historical data for rule {rule_id}: {len(historical_data)} samples")
                return []
            
            # Apply selected detection method
            detection_method = self.methods.get(method, self._detect_statistical_anomaly)
            results = detection_method(historical_data, sensitivity)
            
            # Store anomaly results
            self._store_anomaly_results(rule_id, results, method)
            
            return results
            
        except Exception as e:
            logger.error(f"Error detecting anomalies for rule {rule_id}: {str(e)}")
            return []
    
    def detect_volume_anomalies(
        self,
        rule_id: int,
        current_volume: int,
        time_window: str = "24h",
        method: str = "statistical"
    ) -> AnomalyResult:
        """Detect volume anomalies for row count or data ingestion volume."""
        try:
            # Parse time window
            hours = self._parse_time_window(time_window)
            since_time = timezone.now() - timedelta(hours=hours)
            
            # Get volume history
            volume_history = self._get_volume_history(rule_id, since_time)
            
            if len(volume_history) < 5:  # Need minimum samples
                return AnomalyResult(
                    is_anomaly=False,
                    confidence=0.0,
                    method=method,
                    threshold_value=0,
                    actual_value=current_volume,
                    expected_range=(0, float('inf')),
                    context={'reason': 'insufficient_data'}
                )
            
            # Apply detection method
            if method == "statistical":
                return self._detect_volume_statistical_anomaly(volume_history, current_volume)
            elif method == "z_score":
                return self._detect_volume_zscore_anomaly(volume_history, current_volume)
            else:
                return self._detect_volume_iqr_anomaly(volume_history, current_volume)
                
        except Exception as e:
            logger.error(f"Error detecting volume anomalies: {str(e)}")
            return AnomalyResult(
                is_anomaly=False,
                confidence=0.0,
                method=method,
                threshold_value=0,
                actual_value=current_volume,
                expected_range=(0, float('inf')),
                context={'error': str(e)}
            )
    
    def detect_pattern_anomalies(
        self,
        rule_id: int,
        pattern_type: str = "daily",
        lookback_days: int = 30
    ) -> List[AnomalyResult]:
        """Detect pattern-based anomalies (daily, weekly, seasonal)."""
        try:
            # Get time-series data
            ts_data = self._get_timeseries_data(rule_id, lookback_days)
            
            if len(ts_data) < 14:  # Need at least 2 weeks for pattern detection
                return []
            
            # Convert to pandas DataFrame for easier manipulation
            df = pd.DataFrame(ts_data)
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            df.set_index('timestamp', inplace=True)
            
            if pattern_type == "daily":
                return self._detect_daily_pattern_anomalies(df)
            elif pattern_type == "weekly":
                return self._detect_weekly_pattern_anomalies(df)
            elif pattern_type == "seasonal":
                return self._detect_seasonal_pattern_anomalies(df)
            else:
                return []
                
        except Exception as e:
            logger.error(f"Error detecting pattern anomalies: {str(e)}")
            return []
    
    def _get_historical_data(self, rule_id: int, lookback_days: int) -> List[Dict]:
        """Get historical DQ run data for anomaly detection."""
        since_date = timezone.now() - timedelta(days=lookback_days)
        
        runs = DQRun.objects.filter(
            rule_id=rule_id,
            finished_at__gte=since_date,
            status=DQRunStatus.SUCCESS
        ).order_by('finished_at').values(
            'id', 'finished_at', 'violations_count', 'rows_scanned', 'duration_seconds'
        )
        
        return list(runs)
    
    def _get_volume_history(self, rule_id: int, since_time: datetime) -> List[int]:
        """Get volume history for anomaly detection."""
        runs = DQRun.objects.filter(
            rule_id=rule_id,
            finished_at__gte=since_time,
            status=DQRunStatus.SUCCESS
        ).order_by('finished_at').values_list('rows_scanned', flat=True)
        
        return [vol for vol in runs if vol is not None and vol > 0]
    
    def _get_timeseries_data(self, rule_id: int, lookback_days: int) -> List[Dict]:
        """Get time-series data for pattern anomaly detection."""
        since_date = timezone.now() - timedelta(days=lookback_days)
        
        runs = DQRun.objects.filter(
            rule_id=rule_id,
            finished_at__gte=since_date,
            status=DQRunStatus.SUCCESS
        ).order_by('finished_at').values(
            'finished_at', 'violations_count', 'rows_scanned'
        )
        
        return [
            {
                'timestamp': run['finished_at'],
                'violations': run['violations_count'],
                'volume': run['rows_scanned'] or 0
            }
            for run in runs
        ]
    
    def _detect_statistical_anomaly(
        self, 
        historical_data: List[Dict], 
        sensitivity: float = 0.05
    ) -> List[AnomalyResult]:
        """Statistical anomaly detection using mean and standard deviation."""
        results = []
        
        try:
            # Extract violation counts
            violations = [run['violations_count'] for run in historical_data]
            
            if len(violations) < 3:
                return results
            
            # Calculate statistics
            mean_violations = np.mean(violations)
            std_violations = np.std(violations)
            
            # Z-score threshold based on sensitivity
            z_threshold = stats.norm.ppf(1 - sensitivity/2)  # Two-tailed test
            
            # Check recent values for anomalies
            recent_runs = historical_data[-5:]  # Check last 5 runs
            
            for run in recent_runs:
                violations_count = run['violations_count']
                
                if std_violations > 0:
                    z_score = abs((violations_count - mean_violations) / std_violations)
                    is_anomaly = z_score > z_threshold
                    confidence = min(z_score / z_threshold, 1.0) if is_anomaly else 0.0
                else:
                    is_anomaly = violations_count != mean_violations
                    confidence = 1.0 if is_anomaly else 0.0
                
                expected_range = (
                    max(0, mean_violations - z_threshold * std_violations),
                    mean_violations + z_threshold * std_violations
                )
                
                result = AnomalyResult(
                    is_anomaly=is_anomaly,
                    confidence=confidence,
                    method="statistical",
                    threshold_value=z_threshold,
                    actual_value=violations_count,
                    expected_range=expected_range,
                    context={
                        'run_id': run['id'],
                        'mean': mean_violations,
                        'std': std_violations,
                        'z_score': z_score
                    }
                )
                results.append(result)
            
        except Exception as e:
            logger.error(f"Error in statistical anomaly detection: {str(e)}")
        
        return results
    
    def _detect_isolation_forest_anomaly(
        self, 
        historical_data: List[Dict], 
        sensitivity: float = 0.05
    ) -> List[AnomalyResult]:
        """Isolation Forest anomaly detection."""
        results = []
        
        try:
            # Prepare feature matrix
            features = np.array([
                [
                    run['violations_count'],
                    run['rows_scanned'] or 0,
                    run['duration_seconds'] or 0
                ]
                for run in historical_data
            ])
            
            if len(features) < 10:  # Need sufficient samples for Isolation Forest
                return results
            
            # Scale features
            scaler = StandardScaler()
            features_scaled = scaler.fit_transform(features)
            
            # Train Isolation Forest
            contamination = min(sensitivity, 0.3)  # Cap contamination rate
            iso_forest = IsolationForest(
                contamination=contamination,
                random_state=42,
                n_estimators=100
            )
            iso_forest.fit(features_scaled)
            
            # Predict anomalies and get scores
            predictions = iso_forest.predict(features_scaled)
            scores = iso_forest.decision_function(features_scaled)
            
            # Process recent runs
            recent_runs = historical_data[-5:]
            recent_predictions = predictions[-5:]
            recent_scores = scores[-5:]
            
            for i, run in enumerate(recent_runs):
                is_anomaly = recent_predictions[i] == -1
                confidence = abs(recent_scores[i]) if is_anomaly else 0.0
                
                result = AnomalyResult(
                    is_anomaly=is_anomaly,
                    confidence=confidence,
                    method="isolation_forest",
                    threshold_value=contamination,
                    actual_value=run['violations_count'],
                    expected_range=(0, float('inf')),  # IF doesn't provide explicit ranges
                    context={
                        'run_id': run['id'],
                        'anomaly_score': recent_scores[i]
                    }
                )
                results.append(result)
                
        except Exception as e:
            logger.error(f"Error in Isolation Forest anomaly detection: {str(e)}")
        
        return results
    
    def _detect_zscore_anomaly(
        self, 
        historical_data: List[Dict], 
        sensitivity: float = 0.05
    ) -> List[AnomalyResult]:
        """Z-score based anomaly detection."""
        results = []
        
        try:
            violations = [run['violations_count'] for run in historical_data]
            
            if len(violations) < 3:
                return results
            
            violations_array = np.array(violations)
            z_scores = np.abs(stats.zscore(violations_array))
            
            # Z-score threshold
            z_threshold = 3.0  # Standard 3-sigma rule
            if sensitivity < 0.01:
                z_threshold = 3.5
            elif sensitivity > 0.05:
                z_threshold = 2.5
            
            # Check recent runs
            recent_runs = historical_data[-5:]
            recent_z_scores = z_scores[-5:]
            
            mean_violations = np.mean(violations)
            std_violations = np.std(violations)
            
            for i, run in enumerate(recent_runs):
                z_score = recent_z_scores[i]
                is_anomaly = z_score > z_threshold
                confidence = min(z_score / z_threshold, 1.0) if is_anomaly else 0.0
                
                expected_range = (
                    max(0, mean_violations - z_threshold * std_violations),
                    mean_violations + z_threshold * std_violations
                )
                
                result = AnomalyResult(
                    is_anomaly=is_anomaly,
                    confidence=confidence,
                    method="z_score",
                    threshold_value=z_threshold,
                    actual_value=run['violations_count'],
                    expected_range=expected_range,
                    context={
                        'run_id': run['id'],
                        'z_score': z_score
                    }
                )
                results.append(result)
                
        except Exception as e:
            logger.error(f"Error in Z-score anomaly detection: {str(e)}")
        
        return results
    
    def _detect_iqr_anomaly(
        self, 
        historical_data: List[Dict], 
        sensitivity: float = 0.05
    ) -> List[AnomalyResult]:
        """IQR-based anomaly detection."""
        results = []
        
        try:
            violations = [run['violations_count'] for run in historical_data]
            
            if len(violations) < 5:
                return results
            
            violations_array = np.array(violations)
            Q1 = np.percentile(violations_array, 25)
            Q3 = np.percentile(violations_array, 75)
            IQR = Q3 - Q1
            
            # Adjust multiplier based on sensitivity
            multiplier = 1.5
            if sensitivity < 0.01:
                multiplier = 2.0
            elif sensitivity > 0.05:
                multiplier = 1.0
            
            lower_bound = Q1 - multiplier * IQR
            upper_bound = Q3 + multiplier * IQR
            
            # Check recent runs
            recent_runs = historical_data[-5:]
            
            for run in recent_runs:
                violations_count = run['violations_count']
                is_anomaly = violations_count < lower_bound or violations_count > upper_bound
                
                if is_anomaly:
                    distance_from_bounds = min(
                        abs(violations_count - lower_bound),
                        abs(violations_count - upper_bound)
                    )
                    confidence = min(distance_from_bounds / (IQR * multiplier), 1.0)
                else:
                    confidence = 0.0
                
                result = AnomalyResult(
                    is_anomaly=is_anomaly,
                    confidence=confidence,
                    method="iqr",
                    threshold_value=multiplier,
                    actual_value=violations_count,
                    expected_range=(max(0, lower_bound), upper_bound),
                    context={
                        'run_id': run['id'],
                        'Q1': Q1,
                        'Q3': Q3,
                        'IQR': IQR
                    }
                )
                results.append(result)
                
        except Exception as e:
            logger.error(f"Error in IQR anomaly detection: {str(e)}")
        
        return results
    
    def _detect_seasonal_anomaly(
        self, 
        historical_data: List[Dict], 
        sensitivity: float = 0.05
    ) -> List[AnomalyResult]:
        """Seasonal decomposition anomaly detection."""
        # This would require more sophisticated time series analysis
        # For now, return empty results
        logger.info("Seasonal anomaly detection not yet implemented")
        return []
    
    def _detect_change_point_anomaly(
        self, 
        historical_data: List[Dict], 
        sensitivity: float = 0.05
    ) -> List[AnomalyResult]:
        """Change point detection for identifying shifts in data patterns."""
        results = []
        
        try:
            violations = [run['violations_count'] for run in historical_data]
            
            if len(violations) < 10:
                return results
            
            violations_array = np.array(violations)
            
            # Simple change point detection using moving averages
            window_size = min(len(violations) // 4, 10)
            moving_avg = pd.Series(violations).rolling(window=window_size).mean().values
            
            # Find significant changes in moving average
            changes = np.diff(moving_avg)
            change_threshold = np.std(changes) * (3.0 if sensitivity < 0.05 else 2.0)
            
            change_points = find_peaks(np.abs(changes), height=change_threshold)[0]
            
            # Check if recent data points are near change points
            recent_start = len(violations) - 5
            for i, run in enumerate(historical_data[-5:]):
                position = recent_start + i
                
                # Check if position is near a change point
                is_anomaly = any(abs(position - cp) <= 2 for cp in change_points)
                
                if is_anomaly:
                    nearest_cp = min(change_points, key=lambda cp: abs(position - cp))
                    confidence = 1.0 / (abs(position - nearest_cp) + 1)
                else:
                    confidence = 0.0
                
                result = AnomalyResult(
                    is_anomaly=is_anomaly,
                    confidence=confidence,
                    method="change_point",
                    threshold_value=change_threshold,
                    actual_value=run['violations_count'],
                    expected_range=(0, float('inf')),
                    context={
                        'run_id': run['id'],
                        'change_points': change_points.tolist(),
                        'position': position
                    }
                )
                results.append(result)
                
        except Exception as e:
            logger.error(f"Error in change point anomaly detection: {str(e)}")
        
        return results
    
    def _detect_volume_statistical_anomaly(
        self, 
        volume_history: List[int], 
        current_volume: int
    ) -> AnomalyResult:
        """Statistical anomaly detection for volume data."""
        mean_volume = np.mean(volume_history)
        std_volume = np.std(volume_history)
        
        if std_volume > 0:
            z_score = abs((current_volume - mean_volume) / std_volume)
            is_anomaly = z_score > 3.0
            confidence = min(z_score / 3.0, 1.0) if is_anomaly else 0.0
        else:
            is_anomaly = current_volume != mean_volume
            confidence = 1.0 if is_anomaly else 0.0
            z_score = 0.0
        
        expected_range = (
            max(0, mean_volume - 3.0 * std_volume),
            mean_volume + 3.0 * std_volume
        )
        
        return AnomalyResult(
            is_anomaly=is_anomaly,
            confidence=confidence,
            method="volume_statistical",
            threshold_value=3.0,
            actual_value=current_volume,
            expected_range=expected_range,
            context={
                'mean': mean_volume,
                'std': std_volume,
                'z_score': z_score,
                'history_size': len(volume_history)
            }
        )
    
    def _detect_volume_zscore_anomaly(
        self, 
        volume_history: List[int], 
        current_volume: int
    ) -> AnomalyResult:
        """Z-score anomaly detection for volume data."""
        return self._detect_volume_statistical_anomaly(volume_history, current_volume)
    
    def _detect_volume_iqr_anomaly(
        self, 
        volume_history: List[int], 
        current_volume: int
    ) -> AnomalyResult:
        """IQR anomaly detection for volume data."""
        volume_array = np.array(volume_history)
        Q1 = np.percentile(volume_array, 25)
        Q3 = np.percentile(volume_array, 75)
        IQR = Q3 - Q1
        
        multiplier = 1.5
        lower_bound = Q1 - multiplier * IQR
        upper_bound = Q3 + multiplier * IQR
        
        is_anomaly = current_volume < lower_bound or current_volume > upper_bound
        
        if is_anomaly:
            distance_from_bounds = min(
                abs(current_volume - lower_bound),
                abs(current_volume - upper_bound)
            )
            confidence = min(distance_from_bounds / (IQR * multiplier), 1.0)
        else:
            confidence = 0.0
        
        return AnomalyResult(
            is_anomaly=is_anomaly,
            confidence=confidence,
            method="volume_iqr",
            threshold_value=multiplier,
            actual_value=current_volume,
            expected_range=(max(0, lower_bound), upper_bound),
            context={
                'Q1': Q1,
                'Q3': Q3,
                'IQR': IQR,
                'history_size': len(volume_history)
            }
        )
    
    def _parse_time_window(self, time_window: str) -> int:
        """Parse time window string to hours."""
        if time_window.endswith('h'):
            return int(time_window[:-1])
        elif time_window.endswith('d'):
            return int(time_window[:-1]) * 24
        else:
            return 24  # Default to 24 hours
    
    def _store_anomaly_results(
        self, 
        rule_id: int, 
        results: List[AnomalyResult], 
        method: str
    ) -> None:
        """Store anomaly detection results in the database."""
        try:
            rule = DQRule.objects.get(id=rule_id)
            
            for result in results:
                if result.is_anomaly:
                    DQAnomalyDetection.objects.create(
                        rule=rule,
                        run_id=result.context.get('run_id'),
                        detection_method=method,
                        anomaly_score=result.confidence,
                        threshold_value=result.threshold_value,
                        actual_value=result.actual_value,
                        expected_range_min=result.expected_range[0],
                        expected_range_max=result.expected_range[1],
                        context=result.context,
                        detected_at=timezone.now()
                    )
                    
        except Exception as e:
            logger.error(f"Error storing anomaly results: {str(e)}")


# Global anomaly detector instance
dq_anomaly_detector = DQAnomalyDetector()