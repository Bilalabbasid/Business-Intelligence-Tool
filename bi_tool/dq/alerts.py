"""
Data Quality Alerting and Escalation System
Handles notifications for DQ violations with multi-channel support.
"""

import logging
import json
import smtplib
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

import requests
from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

from .models import DQRule, DQRun, DQViolation, DQSeverity

logger = logging.getLogger(__name__)


class DQAlertManager:
    """Manages data quality alerts across multiple channels."""
    
    def __init__(self):
        self.email_config = getattr(settings, 'DQ_EMAIL_CONFIG', {})
        self.slack_config = getattr(settings, 'DQ_SLACK_CONFIG', {})
        self.pagerduty_config = getattr(settings, 'DQ_PAGERDUTY_CONFIG', {})
        self.alert_rules = getattr(settings, 'DQ_ALERT_RULES', {})
    
    def send_alert(self, alert_data: Dict[str, Any]) -> Dict[str, bool]:
        """Send alert through appropriate channels based on severity and configuration."""
        results = {
            'email': False,
            'slack': False,
            'pagerduty': False
        }
        
        severity = alert_data.get('severity', 'MEDIUM')
        rule_name = alert_data.get('rule_name', 'unknown')
        
        try:
            # Determine alert channels based on severity
            channels = self._get_alert_channels(severity)
            
            # Send email alerts
            if 'email' in channels:
                results['email'] = self._send_email_alert(alert_data)
            
            # Send Slack alerts
            if 'slack' in channels:
                results['slack'] = self._send_slack_alert(alert_data)
            
            # Send PagerDuty alerts for critical issues
            if 'pagerduty' in channels and severity in ['CRITICAL', 'HIGH']:
                results['pagerduty'] = self._send_pagerduty_alert(alert_data)
            
            logger.info(f"Alert sent for rule {rule_name}: {results}")
            
        except Exception as e:
            logger.error(f"Error sending alert for rule {rule_name}: {str(e)}")
        
        return results
    
    def send_batch_alert(self, batch_summary: Dict[str, Any]) -> bool:
        """Send alert for batch job summary."""
        try:
            if batch_summary.get('failed', 0) > 0 or batch_summary.get('total_violations', 0) > 10:
                
                # Prepare batch alert data
                alert_data = {
                    'type': 'batch_alert',
                    'batch_name': batch_summary.get('batch_name', 'unknown'),
                    'total_rules': batch_summary.get('total_rules', 0),
                    'successful': batch_summary.get('successful', 0),
                    'failed': batch_summary.get('failed', 0),
                    'total_violations': batch_summary.get('total_violations', 0),
                    'executed_at': batch_summary.get('executed_at'),
                    'results': batch_summary.get('results', [])
                }
                
                # Send to appropriate channels
                self._send_email_batch_alert(alert_data)
                self._send_slack_batch_alert(alert_data)
                
                return True
                
        except Exception as e:
            logger.error(f"Error sending batch alert: {str(e)}")
            
        return False
    
    def _get_alert_channels(self, severity: str) -> List[str]:
        """Determine alert channels based on severity."""
        severity_mapping = {
            'CRITICAL': ['email', 'slack', 'pagerduty'],
            'HIGH': ['email', 'slack'],
            'MEDIUM': ['email'],
            'LOW': ['slack'],
            'INFO': []
        }
        
        return severity_mapping.get(severity, ['email'])
    
    def _send_email_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Send email alert for DQ violation."""
        try:
            if not self.email_config or not self.email_config.get('enabled', False):
                return False
            
            # Prepare email content
            subject = self._generate_email_subject(alert_data)
            body = self._generate_email_body(alert_data)
            recipients = self._get_email_recipients(alert_data)
            
            if not recipients:
                logger.warning(f"No email recipients found for rule: {alert_data.get('rule_name')}")
                return False
            
            # Send email
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.email_config.get('from_address')
            msg['To'] = ', '.join(recipients)
            
            # Attach HTML and plain text versions
            msg.attach(MIMEText(body['text'], 'plain'))
            msg.attach(MIMEText(body['html'], 'html'))
            
            # Send via SMTP
            with smtplib.SMTP(
                self.email_config.get('smtp_host'),
                self.email_config.get('smtp_port', 587)
            ) as server:
                if self.email_config.get('use_tls', True):
                    server.starttls()
                
                if self.email_config.get('username'):
                    server.login(
                        self.email_config.get('username'),
                        self.email_config.get('password')
                    )
                
                server.send_message(msg)
            
            logger.info(f"Email alert sent for rule: {alert_data.get('rule_name')}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending email alert: {str(e)}")
            return False
    
    def _send_slack_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Send Slack alert for DQ violation."""
        try:
            if not self.slack_config or not self.slack_config.get('webhook_url'):
                return False
            
            # Generate Slack message
            message = self._generate_slack_message(alert_data)
            
            # Send to Slack
            response = requests.post(
                self.slack_config['webhook_url'],
                json=message,
                timeout=10
            )
            response.raise_for_status()
            
            logger.info(f"Slack alert sent for rule: {alert_data.get('rule_name')}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending Slack alert: {str(e)}")
            return False
    
    def _send_pagerduty_alert(self, alert_data: Dict[str, Any]) -> bool:
        """Send PagerDuty alert for critical DQ violations."""
        try:
            if not self.pagerduty_config or not self.pagerduty_config.get('integration_key'):
                return False
            
            # Generate PagerDuty event
            event_data = {
                'routing_key': self.pagerduty_config['integration_key'],
                'event_action': 'trigger',
                'dedup_key': f"dq_violation_{alert_data.get('rule_name')}_{alert_data.get('run_id')}",
                'payload': {
                    'summary': f"DQ Violation: {alert_data.get('rule_name')} - {alert_data.get('violations_count')} violations",
                    'severity': alert_data.get('severity', '').lower(),
                    'source': alert_data.get('target', 'unknown'),
                    'component': 'data-quality',
                    'group': 'bi-platform',
                    'class': alert_data.get('check_type', 'unknown'),
                    'custom_details': {
                        'rule_name': alert_data.get('rule_name'),
                        'violations_count': alert_data.get('violations_count'),
                        'threshold': alert_data.get('threshold'),
                        'run_id': alert_data.get('run_id'),
                        'detected_at': alert_data.get('detected_at'),
                        'owners': alert_data.get('owners', [])
                    }
                }
            }
            
            # Send to PagerDuty Events API
            response = requests.post(
                'https://events.pagerduty.com/v2/enqueue',
                json=event_data,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            response.raise_for_status()
            
            logger.info(f"PagerDuty alert sent for rule: {alert_data.get('rule_name')}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending PagerDuty alert: {str(e)}")
            return False
    
    def _generate_email_subject(self, alert_data: Dict[str, Any]) -> str:
        """Generate email subject for DQ alert."""
        severity = alert_data.get('severity', 'MEDIUM')
        rule_name = alert_data.get('rule_name', 'unknown')
        violations_count = alert_data.get('violations_count', 0)
        
        emoji_map = {
            'CRITICAL': '🚨',
            'HIGH': '⚠️',
            'MEDIUM': '⚡',
            'LOW': '📊',
            'INFO': 'ℹ️'
        }
        
        emoji = emoji_map.get(severity, '📊')
        return f"{emoji} [{severity}] Data Quality Alert: {rule_name} ({violations_count} violations)"
    
    def _generate_email_body(self, alert_data: Dict[str, Any]) -> Dict[str, str]:
        """Generate email body content (HTML and text versions)."""
        context = {
            'alert_data': alert_data,
            'dashboard_url': getattr(settings, 'DQ_DASHBOARD_URL', '#'),
            'generated_at': timezone.now().strftime('%Y-%m-%d %H:%M:%S UTC')
        }
        
        # Generate HTML version
        html_body = f"""
        <html>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
            <h2 style="color: #d73527;">Data Quality Alert</h2>
            
            <div style="background-color: #f8f9fa; padding: 15px; border-left: 4px solid #d73527; margin: 20px 0;">
                <h3>{alert_data.get('rule_name', 'Unknown Rule')}</h3>
                <p><strong>Severity:</strong> {alert_data.get('severity', 'MEDIUM')}</p>
                <p><strong>Check Type:</strong> {alert_data.get('check_type', 'unknown')}</p>
                <p><strong>Target:</strong> {alert_data.get('target', 'unknown')}</p>
                <p><strong>Violations Count:</strong> {alert_data.get('violations_count', 0)}</p>
                <p><strong>Threshold:</strong> {alert_data.get('threshold', 'N/A')}</p>
                <p><strong>Detected At:</strong> {alert_data.get('detected_at', 'unknown')}</p>
            </div>
            
            <h4>Owners:</h4>
            <ul>
                {"".join(f"<li>{owner}</li>" for owner in alert_data.get('owners', []))}
            </ul>
            
            <p><a href="{context['dashboard_url']}/runs/{alert_data.get('run_id', '')}" 
                  style="background-color: #007bff; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">
                View Details
            </a></p>
            
            <hr style="margin: 30px 0;">
            <small style="color: #6c757d;">
                Generated at {context['generated_at']} by BI Platform Data Quality System
            </small>
        </body>
        </html>
        """
        
        # Generate text version
        text_body = f"""
Data Quality Alert

Rule: {alert_data.get('rule_name', 'Unknown Rule')}
Severity: {alert_data.get('severity', 'MEDIUM')}
Check Type: {alert_data.get('check_type', 'unknown')}
Target: {alert_data.get('target', 'unknown')}
Violations Count: {alert_data.get('violations_count', 0)}
Threshold: {alert_data.get('threshold', 'N/A')}
Detected At: {alert_data.get('detected_at', 'unknown')}

Owners: {', '.join(alert_data.get('owners', []))}

View Details: {context['dashboard_url']}/runs/{alert_data.get('run_id', '')}

Generated at {context['generated_at']} by BI Platform Data Quality System
        """
        
        return {'html': html_body, 'text': text_body}
    
    def _generate_slack_message(self, alert_data: Dict[str, Any]) -> Dict[str, Any]:
        """Generate Slack message for DQ alert."""
        severity = alert_data.get('severity', 'MEDIUM')
        color_map = {
            'CRITICAL': '#d73527',
            'HIGH': '#fd7e14',
            'MEDIUM': '#ffc107',
            'LOW': '#28a745',
            'INFO': '#17a2b8'
        }
        
        emoji_map = {
            'CRITICAL': '🚨',
            'HIGH': '⚠️',
            'MEDIUM': '⚡',
            'LOW': '📊',
            'INFO': 'ℹ️'
        }
        
        return {
            'text': f"{emoji_map.get(severity, '📊')} Data Quality Alert",
            'attachments': [
                {
                    'color': color_map.get(severity, '#ffc107'),
                    'title': f"{alert_data.get('rule_name', 'Unknown Rule')}",
                    'fields': [
                        {
                            'title': 'Severity',
                            'value': severity,
                            'short': True
                        },
                        {
                            'title': 'Violations',
                            'value': str(alert_data.get('violations_count', 0)),
                            'short': True
                        },
                        {
                            'title': 'Check Type',
                            'value': alert_data.get('check_type', 'unknown'),
                            'short': True
                        },
                        {
                            'title': 'Target',
                            'value': alert_data.get('target', 'unknown'),
                            'short': True
                        },
                        {
                            'title': 'Threshold',
                            'value': str(alert_data.get('threshold', 'N/A')),
                            'short': True
                        },
                        {
                            'title': 'Run ID',
                            'value': str(alert_data.get('run_id', 'unknown')),
                            'short': True
                        }
                    ],
                    'footer': 'BI Platform Data Quality',
                    'ts': int(timezone.now().timestamp())
                }
            ]
        }
    
    def _send_email_batch_alert(self, batch_data: Dict[str, Any]) -> bool:
        """Send email alert for batch job summary."""
        try:
            if not self.email_config or not self.email_config.get('enabled', False):
                return False
            
            subject = f"📊 DQ Batch Summary: {batch_data.get('batch_name', 'unknown')} - {batch_data.get('failed', 0)} failures"
            
            # Generate batch summary email
            html_body = f"""
            <html>
            <body style="font-family: Arial, sans-serif;">
                <h2>Data Quality Batch Summary</h2>
                <h3>Batch: {batch_data.get('batch_name', 'unknown')}</h3>
                
                <div style="background-color: #f8f9fa; padding: 15px; margin: 20px 0;">
                    <p><strong>Total Rules:</strong> {batch_data.get('total_rules', 0)}</p>
                    <p><strong>Successful:</strong> {batch_data.get('successful', 0)}</p>
                    <p><strong>Failed:</strong> {batch_data.get('failed', 0)}</p>
                    <p><strong>Total Violations:</strong> {batch_data.get('total_violations', 0)}</p>
                    <p><strong>Executed At:</strong> {batch_data.get('executed_at', 'unknown')}</p>
                </div>
                
                <h4>Failed Rules:</h4>
                <ul>
                    {"".join(f"<li>{result.get('error', 'Unknown error')} (Rule ID: {result.get('rule_id', 'unknown')})</li>" 
                            for result in batch_data.get('results', []) if not result.get('success'))}
                </ul>
            </body>
            </html>
            """
            
            # Send to DQ admins
            admin_emails = self.email_config.get('admin_emails', [])
            if admin_emails:
                msg = MIMEMultipart()
                msg['Subject'] = subject
                msg['From'] = self.email_config.get('from_address')
                msg['To'] = ', '.join(admin_emails)
                msg.attach(MIMEText(html_body, 'html'))
                
                with smtplib.SMTP(
                    self.email_config.get('smtp_host'),
                    self.email_config.get('smtp_port', 587)
                ) as server:
                    if self.email_config.get('use_tls', True):
                        server.starttls()
                    if self.email_config.get('username'):
                        server.login(
                            self.email_config.get('username'),
                            self.email_config.get('password')
                        )
                    server.send_message(msg)
                
                return True
                
        except Exception as e:
            logger.error(f"Error sending batch email alert: {str(e)}")
            
        return False
    
    def _send_slack_batch_alert(self, batch_data: Dict[str, Any]) -> bool:
        """Send Slack alert for batch job summary."""
        try:
            if not self.slack_config or not self.slack_config.get('webhook_url'):
                return False
            
            color = '#d73527' if batch_data.get('failed', 0) > 0 else '#28a745'
            
            message = {
                'text': f"📊 DQ Batch Summary: {batch_data.get('batch_name', 'unknown')}",
                'attachments': [
                    {
                        'color': color,
                        'fields': [
                            {
                                'title': 'Total Rules',
                                'value': str(batch_data.get('total_rules', 0)),
                                'short': True
                            },
                            {
                                'title': 'Successful',
                                'value': str(batch_data.get('successful', 0)),
                                'short': True
                            },
                            {
                                'title': 'Failed',
                                'value': str(batch_data.get('failed', 0)),
                                'short': True
                            },
                            {
                                'title': 'Total Violations',
                                'value': str(batch_data.get('total_violations', 0)),
                                'short': True
                            }
                        ],
                        'footer': 'BI Platform Data Quality',
                        'ts': int(timezone.now().timestamp())
                    }
                ]
            }
            
            response = requests.post(
                self.slack_config['webhook_url'],
                json=message,
                timeout=10
            )
            response.raise_for_status()
            
            return True
            
        except Exception as e:
            logger.error(f"Error sending batch Slack alert: {str(e)}")
            
        return False
    
    def _get_email_recipients(self, alert_data: Dict[str, Any]) -> List[str]:
        """Get email recipients for alert based on rule owners and severity."""
        recipients = []
        
        # Add rule owners
        owners = alert_data.get('owners', [])
        recipients.extend(owners)
        
        # Add severity-based recipients
        severity = alert_data.get('severity', 'MEDIUM')
        if severity in ['CRITICAL', 'HIGH']:
            admin_emails = self.email_config.get('admin_emails', [])
            recipients.extend(admin_emails)
        
        # Remove duplicates and filter valid emails
        recipients = list(set(email for email in recipients if '@' in email))
        
        return recipients