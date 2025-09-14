"""
Django management command to load DQ rules from YAML manifest files.
"""

import os
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from dq.rules import dq_registry


class Command(BaseCommand):
    help = 'Load data quality rules from YAML manifest files'

    def add_arguments(self, parser):
        parser.add_argument(
            'manifest_file',
            type=str,
            help='Path to the YAML manifest file'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Validate manifest without creating rules',
        )
        
        parser.add_argument(
            '--force',
            action='store_true',
            help='Overwrite existing rules with same names',
        )

    def handle(self, *args, **options):
        manifest_file = options['manifest_file']
        dry_run = options['dry_run']
        force = options['force']
        
        # Check if file exists
        if not os.path.exists(manifest_file):
            raise CommandError(f'Manifest file does not exist: {manifest_file}')
        
        self.stdout.write(f'Loading DQ rules from: {manifest_file}')
        
        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No rules will be created'))
        
        try:
            # Load rules from manifest
            results = dq_registry.load_rules_from_manifest(manifest_file)
            
            # Display results
            self.stdout.write(
                self.style.SUCCESS(
                    f'Successfully loaded {results["loaded"]} rules'
                )
            )
            
            if results.get('skipped', 0) > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f'Skipped {results["skipped"]} rules due to validation errors'
                    )
                )
            
            # Display any errors
            if results.get('errors'):
                self.stdout.write(self.style.ERROR('Errors encountered:'))
                for error in results['errors']:
                    self.stdout.write(f'  - {error}')
            
        except Exception as e:
            raise CommandError(f'Failed to load manifest: {str(e)}')