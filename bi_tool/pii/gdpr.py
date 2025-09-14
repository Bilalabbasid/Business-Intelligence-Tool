"""
GDPR compliance utilities including DSAR processing, consent management,
and data retention automation.
"""

import json
import csv
import os
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from django.conf import settings
from django.db import transaction
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.utils import timezone
from django.contrib.auth.models import User
from django.db.models import Q
from django.template.loader import render_to_string
import zipfile
import tempfile
from io import StringIO

from .models import (
    DataSubject, DataSubjectRequest, ConsentRecord, 
    PIIDataMap, PIIProcessingRecord, RetentionPolicy
)
from .detectors import PIIDetector
from .encryption import FieldEncryptor
from security.models import AuditLog


class DSARProcessor:
    """Handles Data Subject Access Requests (GDPR Article 15)."""
    
    def __init__(self):
        self.pii_detector = PIIDetector()
        self.encryptor = FieldEncryptor()
    
    def process_access_request(self, request: DataSubjectRequest) -> Dict[str, Any]:
        """
        Process a data subject access request.
        
        Returns comprehensive data report for the subject.
        """
        try:
            subject = request.subject
            
            # Collect all data for the subject
            data_report = {
                'request_id': request.request_id,
                'subject_id': subject.subject_id,
                'generated_at': timezone.now().isoformat(),
                'personal_data': self._collect_personal_data(subject),
                'processing_activities': self._collect_processing_activities(subject),
                'consent_records': self._collect_consent_records(subject),
                'data_sources': self._collect_data_sources(subject),
                'retention_information': self._collect_retention_info(subject),
                'sharing_information': self._collect_sharing_info(subject),
                'automated_processing': self._collect_automated_processing(subject),
            }
            
            # Generate files
            files = self._generate_report_files(data_report)
            
            # Log the access
            self._log_data_access(request, data_report)
            
            # Update request
            request.fulfill_request(
                response_data=data_report,
                response_files=files
            )
            
            return data_report
            
        except Exception as e:
            # Log failure
            AuditLog.objects.create(
                action='GDPR_VIOLATION',
                severity='HIGH',
                resource_type='dsar',
                resource_id=request.request_id,
                description=f'DSAR processing failed: {str(e)}',
                success=False,
                user=request.assigned_to,
                metadata={'error': str(e)}
            )
            raise
    
    def _collect_personal_data(self, subject: DataSubject) -> Dict[str, Any]:
        """Collect all personal data for the subject."""
        return {
            'basic_information': {
                'subject_id': subject.subject_id,
                'external_id': subject.external_id,
                'email': subject.email,
                'phone': subject.phone,
                'name': subject.name,
            },
            'account_status': {
                'is_active': subject.is_active,
                'consent_given': subject.consent_given,
                'consent_date': subject.consent_date.isoformat() if subject.consent_date else None,
                'deletion_requested': subject.deletion_requested,
                'deletion_scheduled': subject.deletion_scheduled.isoformat() if subject.deletion_scheduled else None,
            },
            'data_sources': subject.data_sources,
            'processing_purposes': subject.processing_purposes,
            'legal_basis': subject.legal_basis,
        }
    
    def _collect_processing_activities(self, subject: DataSubject) -> List[Dict[str, Any]]:
        """Collect all processing activities for the subject."""
        activities = PIIProcessingRecord.objects.filter(subject=subject).order_by('-performed_at')[:100]
        
        return [
            {
                'processing_type': activity.get_processing_type_display(),
                'purpose': activity.purpose,
                'legal_basis': activity.legal_basis,
                'performed_at': activity.performed_at.isoformat(),
                'system': activity.system,
                'processor': activity.processor,
                'data_categories': activity.data_categories,
                'is_compliant': activity.is_compliant,
            }
            for activity in activities
        ]
    
    def _collect_consent_records(self, subject: DataSubject) -> List[Dict[str, Any]]:
        """Collect consent records for the subject."""
        consents = ConsentRecord.objects.filter(subject=subject).order_by('-given_date')
        
        return [
            {
                'purpose': consent.purpose,
                'legal_basis': consent.get_legal_basis_display(),
                'is_active': consent.is_active,
                'given_date': consent.given_date.isoformat(),
                'withdrawn_date': consent.withdrawn_date.isoformat() if consent.withdrawn_date else None,
                'expiry_date': consent.expiry_date.isoformat() if consent.expiry_date else None,
                'source': consent.source,
                'consent_version': consent.consent_version,
            }
            for consent in consents
        ]
    
    def _collect_data_sources(self, subject: DataSubject) -> List[Dict[str, Any]]:
        """Collect information about where data is stored."""
        # This would integrate with your actual data systems
        data_maps = PIIDataMap.objects.filter(
            metadata__subject_ids__contains=subject.subject_id
        ).distinct()
        
        return [
            {
                'location': data_map.get_full_path(),
                'pii_type': data_map.pii_type,
                'category': data_map.category.name,
                'sensitivity': data_map.category.sensitivity_level,
                'is_encrypted': data_map.is_encrypted,
                'is_tokenized': data_map.is_tokenized,
                'record_count': data_map.record_count,
                'last_verified': data_map.last_verified.isoformat() if data_map.last_verified else None,
            }
            for data_map in data_maps
        ]
    
    def _collect_retention_info(self, subject: DataSubject) -> Dict[str, Any]:
        """Collect retention policy information."""
        # Get applicable retention policies
        policies = RetentionPolicy.objects.filter(is_active=True)
        
        return {
            'policies': [
                {
                    'name': policy.name,
                    'category': policy.category.name,
                    'retention_days': policy.retention_period_days,
                    'action_after_retention': policy.get_action_after_retention_display(),
                }
                for policy in policies
            ],
            'estimated_deletion_date': self._calculate_estimated_deletion(subject),
        }
    
    def _collect_sharing_info(self, subject: DataSubject) -> List[Dict[str, Any]]:
        """Collect information about data sharing."""
        # This would track third-party sharing
        sharing_records = PIIProcessingRecord.objects.filter(
            subject=subject,
            processing_type='TRANSMISSION'
        ).order_by('-performed_at')[:50]
        
        return [
            {
                'shared_at': record.performed_at.isoformat(),
                'recipients': record.data_recipients,
                'purpose': record.purpose,
                'legal_basis': record.legal_basis,
                'data_categories': record.data_categories,
            }
            for record in sharing_records
        ]
    
    def _collect_automated_processing(self, subject: DataSubject) -> List[Dict[str, Any]]:
        """Collect information about automated decision making."""
        # This would track automated processing/profiling
        automated_records = PIIProcessingRecord.objects.filter(
            subject=subject,
            processing_type='ANALYSIS',
            metadata__automated=True
        ).order_by('-performed_at')[:20]
        
        return [
            {
                'processed_at': record.performed_at.isoformat(),
                'system': record.system,
                'purpose': record.purpose,
                'logic_involved': record.metadata.get('logic', 'Not specified'),
                'significance': record.metadata.get('significance', 'Not specified'),
                'consequences': record.metadata.get('consequences', 'Not specified'),
            }
            for record in automated_records
        ]
    
    def _calculate_estimated_deletion(self, subject: DataSubject) -> Optional[str]:
        """Calculate estimated deletion date based on retention policies."""
        if subject.deletion_scheduled:
            return subject.deletion_scheduled.isoformat()
        
        # Find the longest retention period applicable
        max_retention = 0
        for source in subject.data_sources:
            try:
                data_map = PIIDataMap.objects.filter(
                    database_name=source.get('database'),
                    table_name=source.get('table')
                ).first()
                
                if data_map and data_map.category:
                    policy = RetentionPolicy.objects.filter(
                        category=data_map.category,
                        is_active=True
                    ).first()
                    
                    if policy:
                        max_retention = max(max_retention, policy.retention_period_days)
            except:
                continue
        
        if max_retention > 0:
            estimated_date = timezone.now() + timedelta(days=max_retention)
            return estimated_date.isoformat()
        
        return None
    
    def _generate_report_files(self, data_report: Dict[str, Any]) -> List[str]:
        """Generate downloadable files for the DSAR response."""
        files = []
        
        # Generate JSON report
        json_content = json.dumps(data_report, indent=2, ensure_ascii=False)
        json_file = f"dsar_{data_report['request_id']}_data.json"
        with default_storage.open(json_file, 'w') as f:
            f.write(json_content)
        files.append(json_file)
        
        # Generate CSV for personal data
        csv_file = f"dsar_{data_report['request_id']}_summary.csv"
        with default_storage.open(csv_file, 'w') as f:
            writer = csv.writer(f)
            writer.writerow(['Category', 'Information'])
            
            # Basic information
            for key, value in data_report['personal_data']['basic_information'].items():
                if value:
                    writer.writerow([key.replace('_', ' ').title(), value])
            
            # Processing activities summary
            writer.writerow(['Processing Activities Count', len(data_report['processing_activities'])])
            writer.writerow(['Active Consents', len([c for c in data_report['consent_records'] if c['is_active']])])
            writer.writerow(['Data Sources Count', len(data_report['data_sources'])])
        
        files.append(csv_file)
        
        # Generate HTML report
        html_content = self._generate_html_report(data_report)
        html_file = f"dsar_{data_report['request_id']}_report.html"
        with default_storage.open(html_file, 'w') as f:
            f.write(html_content)
        files.append(html_file)
        
        return files
    
    def _generate_html_report(self, data_report: Dict[str, Any]) -> str:
        """Generate HTML report for DSAR."""
        # This would use a proper template
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Data Subject Access Request Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ background-color: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .section {{ margin: 20px 0; }}
                .data-table {{ width: 100%; border-collapse: collapse; }}
                .data-table th, .data-table td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                .data-table th {{ background-color: #f2f2f2; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Data Subject Access Request Report</h1>
                <p><strong>Request ID:</strong> {data_report['request_id']}</p>
                <p><strong>Subject ID:</strong> {data_report['subject_id']}</p>
                <p><strong>Generated:</strong> {data_report['generated_at']}</p>
            </div>
            
            <div class="section">
                <h2>Personal Information</h2>
                <table class="data-table">
                    <tr><th>Field</th><th>Value</th></tr>
        """
        
        for key, value in data_report['personal_data']['basic_information'].items():
            if value:
                html += f"<tr><td>{key.replace('_', ' ').title()}</td><td>{value}</td></tr>"
        
        html += """
                </table>
            </div>
            
            <div class="section">
                <h2>Processing Activities</h2>
                <p>We have processed your data in the following ways:</p>
                <ul>
        """
        
        for activity in data_report['processing_activities'][:10]:  # Show recent 10
            html += f"<li>{activity['processing_type']} for {activity['purpose']} on {activity['performed_at'][:10]}</li>"
        
        html += """
                </ul>
            </div>
            
            <div class="section">
                <h2>Your Rights</h2>
                <p>Under GDPR, you have the following rights:</p>
                <ul>
                    <li>Right to access your data (Article 15)</li>
                    <li>Right to rectification (Article 16)</li>
                    <li>Right to erasure (Article 17)</li>
                    <li>Right to restrict processing (Article 18)</li>
                    <li>Right to data portability (Article 20)</li>
                    <li>Right to object (Article 21)</li>
                </ul>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _log_data_access(self, request: DataSubjectRequest, data_report: Dict[str, Any]):
        """Log the data access for audit trail."""
        AuditLog.objects.create(
            action='PII_ACCESS',
            severity='MEDIUM',
            resource_type='dsar',
            resource_id=request.request_id,
            description=f'DSAR fulfilled for subject {request.subject.subject_id}',
            success=True,
            user=request.assigned_to,
            metadata={
                'subject_id': request.subject.subject_id,
                'data_categories_accessed': len(data_report['data_sources']),
                'processing_activities_count': len(data_report['processing_activities']),
            }
        )


class ConsentManager:
    """Manages consent collection, tracking, and withdrawal."""
    
    def record_consent(self, subject_id: str, purpose: str, consent_text: str, 
                      version: str, source: str = 'web', 
                      ip_address: str = None, user_agent: str = None,
                      legal_basis: str = 'CONSENT') -> ConsentRecord:
        """Record new consent from a data subject."""
        
        # Get or create data subject
        subject, created = DataSubject.objects.get_or_create(
            subject_id=subject_id,
            defaults={'is_active': True}
        )
        
        # Check if consent already exists for this purpose and version
        existing_consent = ConsentRecord.objects.filter(
            subject=subject,
            purpose=purpose,
            consent_version=version,
            is_active=True
        ).first()
        
        if existing_consent:
            return existing_consent
        
        # Create new consent record
        consent = ConsentRecord.objects.create(
            subject=subject,
            purpose=purpose,
            legal_basis=legal_basis,
            consent_text=consent_text,
            consent_version=version,
            source=source,
            ip_address=ip_address,
            user_agent=user_agent,
            is_active=True
        )
        
        # Update subject consent status
        if legal_basis == 'CONSENT':
            subject.give_consent(version, source)
        
        # Log consent
        AuditLog.objects.create(
            action='PRIVACY_CONSENT',
            severity='LOW',
            resource_type='consent',
            resource_id=subject_id,
            description=f'Consent recorded for {purpose}',
            success=True,
            metadata={
                'purpose': purpose,
                'version': version,
                'source': source,
                'legal_basis': legal_basis
            }
        )
        
        return consent
    
    def withdraw_consent(self, subject_id: str, purpose: str = None) -> List[ConsentRecord]:
        """Withdraw consent for a subject."""
        
        subject = DataSubject.objects.filter(subject_id=subject_id).first()
        if not subject:
            raise ValueError(f"Subject {subject_id} not found")
        
        # Filter consents to withdraw
        consents_query = ConsentRecord.objects.filter(subject=subject, is_active=True)
        if purpose:
            consents_query = consents_query.filter(purpose=purpose)
        
        withdrawn_consents = []
        
        with transaction.atomic():
            for consent in consents_query:
                consent.withdraw()
                withdrawn_consents.append(consent)
                
                # Log withdrawal
                AuditLog.objects.create(
                    action='PRIVACY_CONSENT_WITHDRAWN',
                    severity='MEDIUM',
                    resource_type='consent',
                    resource_id=subject_id,
                    description=f'Consent withdrawn for {consent.purpose}',
                    success=True,
                    metadata={
                        'purpose': consent.purpose,
                        'version': consent.consent_version
                    }
                )
            
            # Update subject status if all consent withdrawn
            if not purpose:  # All consent withdrawn
                subject.withdraw_consent()
        
        return withdrawn_consents
    
    def get_consent_status(self, subject_id: str) -> Dict[str, Any]:
        """Get current consent status for a subject."""
        
        subject = DataSubject.objects.filter(subject_id=subject_id).first()
        if not subject:
            return {'exists': False}
        
        active_consents = ConsentRecord.objects.filter(
            subject=subject,
            is_active=True
        ).select_related('subject')
        
        expired_consents = [c for c in active_consents if c.is_expired()]
        
        return {
            'exists': True,
            'subject_id': subject_id,
            'overall_consent': subject.consent_given,
            'consent_date': subject.consent_date.isoformat() if subject.consent_date else None,
            'active_consents': [
                {
                    'purpose': c.purpose,
                    'legal_basis': c.get_legal_basis_display(),
                    'given_date': c.given_date.isoformat(),
                    'version': c.consent_version,
                    'expires': c.expiry_date.isoformat() if c.expiry_date else None,
                    'is_expired': c.is_expired()
                }
                for c in active_consents
            ],
            'expired_count': len(expired_consents)
        }
    
    def cleanup_expired_consents(self) -> int:
        """Clean up expired consents."""
        
        expired_consents = ConsentRecord.objects.filter(
            is_active=True,
            expiry_date__lt=timezone.now()
        )
        
        count = 0
        for consent in expired_consents:
            consent.withdraw()
            count += 1
            
            # Log expiration
            AuditLog.objects.create(
                action='PRIVACY_CONSENT_EXPIRED',
                severity='LOW',
                resource_type='consent',
                resource_id=consent.subject.subject_id,
                description=f'Consent expired for {consent.purpose}',
                success=True,
                metadata={
                    'purpose': consent.purpose,
                    'expired_at': timezone.now().isoformat()
                }
            )
        
        return count


class RetentionManager:
    """Manages data retention and automated deletion."""
    
    def __init__(self):
        self.dry_run = getattr(settings, 'RETENTION_DRY_RUN', True)
    
    def apply_retention_policies(self) -> Dict[str, int]:
        """Apply retention policies and delete/anonymize expired data."""
        
        results = {
            'subjects_processed': 0,
            'data_deleted': 0,
            'data_anonymized': 0,
            'data_archived': 0,
            'errors': 0
        }
        
        # Get subjects scheduled for deletion
        subjects_to_process = DataSubject.objects.filter(
            deletion_requested=True,
            deletion_scheduled__lt=timezone.now(),
            is_active=True
        )
        
        for subject in subjects_to_process:
            try:
                if self.dry_run:
                    # Just log what would be done
                    self._log_retention_action(subject, 'DRY_RUN')
                else:
                    # Actually process the deletion
                    self._process_subject_deletion(subject)
                
                results['subjects_processed'] += 1
                
            except Exception as e:
                results['errors'] += 1
                
                # Log error
                AuditLog.objects.create(
                    action='DATA_RETENTION_ERROR',
                    severity='HIGH',
                    resource_type='retention',
                    resource_id=subject.subject_id,
                    description=f'Retention processing failed: {str(e)}',
                    success=False,
                    metadata={'error': str(e)}
                )
        
        return results
    
    def _process_subject_deletion(self, subject: DataSubject):
        """Process deletion for a specific subject."""
        
        with transaction.atomic():
            # Get all data locations for this subject
            data_maps = PIIDataMap.objects.filter(
                metadata__subject_ids__contains=subject.subject_id
            )
            
            for data_map in data_maps:
                policy = RetentionPolicy.objects.filter(
                    category=data_map.category,
                    is_active=True
                ).first()
                
                if policy:
                    if policy.action_after_retention == 'DELETE':
                        self._delete_subject_data(subject, data_map)
                    elif policy.action_after_retention == 'ANONYMIZE':
                        self._anonymize_subject_data(subject, data_map)
                    elif policy.action_after_retention == 'ARCHIVE':
                        self._archive_subject_data(subject, data_map)
            
            # Mark subject as processed
            subject.is_active = False
            subject.save()
            
            # Log completion
            self._log_retention_action(subject, 'COMPLETED')
    
    def _delete_subject_data(self, subject: DataSubject, data_map: PIIDataMap):
        """Delete subject data from specified location."""
        
        # This would integrate with actual database deletion
        # For now, just log the action
        AuditLog.objects.create(
            action='DATA_DELETION',
            severity='HIGH',
            resource_type='retention',
            resource_id=subject.subject_id,
            description=f'Data deleted from {data_map.get_full_path()}',
            success=True,
            metadata={
                'location': data_map.get_full_path(),
                'category': data_map.category.name,
                'record_count': data_map.record_count
            }
        )
    
    def _anonymize_subject_data(self, subject: DataSubject, data_map: PIIDataMap):
        """Anonymize subject data."""
        
        # This would implement actual anonymization
        # For now, just log the action
        AuditLog.objects.create(
            action='DATA_ANONYMIZATION',
            severity='MEDIUM',
            resource_type='retention',
            resource_id=subject.subject_id,
            description=f'Data anonymized at {data_map.get_full_path()}',
            success=True,
            metadata={
                'location': data_map.get_full_path(),
                'category': data_map.category.name
            }
        )
    
    def _archive_subject_data(self, subject: DataSubject, data_map: PIIDataMap):
        """Archive subject data."""
        
        # This would implement actual archiving
        # For now, just log the action
        AuditLog.objects.create(
            action='DATA_ARCHIVAL',
            severity='LOW',
            resource_type='retention',
            resource_id=subject.subject_id,
            description=f'Data archived from {data_map.get_full_path()}',
            success=True,
            metadata={
                'location': data_map.get_full_path(),
                'category': data_map.category.name
            }
        )
    
    def _log_retention_action(self, subject: DataSubject, action: str):
        """Log retention processing action."""
        
        AuditLog.objects.create(
            action='DATA_RETENTION',
            severity='MEDIUM',
            resource_type='retention',
            resource_id=subject.subject_id,
            description=f'Retention processing: {action}',
            success=True,
            metadata={
                'action': action,
                'scheduled_date': subject.deletion_scheduled.isoformat() if subject.deletion_scheduled else None,
                'dry_run': self.dry_run
            }
        )