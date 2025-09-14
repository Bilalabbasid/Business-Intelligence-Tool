"""
DSAR Handler for BI Platform

Provides functions to discover, export, anonymize, and track Data Subject Access Requests (DSAR) across MongoDB and PostgreSQL databases.
"""
import os
import json
from datetime import datetime

from pymongo import MongoClient
import psycopg2
from psycopg2.extras import RealDictCursor

# Default PII configuration: tables/collections and their PII fields
PII_CONFIG = {
    'mongo': {
        'users': ['email', 'ssn', 'phone'],
        'customers': ['email', 'phone', 'address']
    },
    'postgres': {
        'public.users': ['email', 'ssn', 'phone'],
        'public.customers': ['email', 'phone', 'address']
    }
}

class DSARHandler:
    def __init__(self, mongo_uri=None, postgres_uri=None, output_dir='ops/requests'):
        self.mongo_uri = mongo_uri or os.getenv('MONGO_URI')
        self.postgres_uri = postgres_uri or os.getenv('POSTGRES_URI')
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

        # Setup Mongo client
        if self.mongo_uri:
            self.mongo_client = MongoClient(self.mongo_uri)
        else:
            self.mongo_client = None

        # Setup Postgres connection
        if self.postgres_uri:
            self.pg_conn = psycopg2.connect(self.postgres_uri, cursor_factory=RealDictCursor)
        else:
            self.pg_conn = None

    def find_pii_mongo(self, db_name, collection_name, filter_field, value):
        """Find documents containing value in filter_field for a MongoDB collection."""
        if not self.mongo_client:
            return []
        db = self.mongo_client[db_name]
        collection = db[collection_name]
        query = {filter_field: value}
        return list(collection.find(query))

    def find_pii_postgres(self, schema_table, filter_field, value):
        """Query Postgres table for rows matching filter_field = value."""
        if not self.pg_conn:
            return []
        with self.pg_conn.cursor() as cur:
            sql = f"SELECT * FROM {schema_table} WHERE {filter_field} = %s"
            cur.execute(sql, (value,))
            return cur.fetchall()

    def anonymize_record(self, record, pii_fields):
        """Remove or mask PII fields in a record."""
        for field in pii_fields:
            if field in record:
                record[field] = None
        return record

    def export_data(self, data, filename):
        """Export data list to JSON file."""
        path = os.path.join(self.output_dir, filename)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, default=str, indent=2)
        return path

    def handle_request(self, subject_id=None, email=None, anonymize=False):
        """
        Main entry point to process a DSAR request.
        Either subject_id or email should be provided.
        """
        identifier = subject_id or email
        timestamp = datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')
        report = {
            'requested_at': timestamp,
            'identifier': identifier,
            'anonymize': anonymize,
            'results': {}
        }

        # Process MongoDB
        if self.mongo_client:
            report['results']['mongo'] = {}
            for coll, fields in PII_CONFIG['mongo'].items():
                docs = self.find_pii_mongo(db_name='default', collection_name=coll,
                                            filter_field='email' if email else 'subject_id', value=identifier)
                if anonymize:
                    docs = [self.anonymize_record(doc, fields) for doc in docs]
                filename = f"mongo_{coll}_{identifier}_{timestamp}.json"
                path = self.export_data(docs, filename)
                report['results']['mongo'][coll] = path

        # Process Postgres
        if self.pg_conn:
            report['results']['postgres'] = {}
            for table, fields in PII_CONFIG['postgres'].items():
                rows = self.find_pii_postgres(schema_table=table,
                                              filter_field='email' if email else 'subject_id', value=identifier)
                if anonymize:
                    rows = [self.anonymize_record(row, fields) for row in rows]
                filename = f"pg_{table.replace('.', '_')}_{identifier}_{timestamp}.json"
                path = self.export_data(rows, filename)
                report['results']['postgres'][table] = path

        # Save request report
        report_file = f"dsar_report_{identifier}_{timestamp}.json"
        report_path = self.export_data(report, report_file)
        return report_path

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='DSAR Handler CLI')
    parser.add_argument('--subject-id', help='Subject ID for DSAR')
    parser.add_argument('--email', help='Email for DSAR')
    parser.add_argument('--anonymize', action='store_true', help='Anonymize PII fields')
    args = parser.parse_args()

    handler = DSARHandler()
    result = handler.handle_request(subject_id=args.subject_id, email=args.email, anonymize=args.anonymize)
    print(f"DSAR report generated: {result}")
