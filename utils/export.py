import pandas as pd
import json
from io import StringIO, BytesIO
import zipfile
from datetime import datetime

class DataExporter:
    @staticmethod
    def to_csv(df, compression=None):
        """Export DataFrame to CSV string with optional compression"""
        if compression == 'zip':
            # Create zip file in memory
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                # Convert DataFrame to CSV and add to zip
                csv_data = df.to_csv(index=False)
                zf.writestr("domain_data.csv", csv_data)
            return zip_buffer.getvalue()
        return df.to_csv(index=False)

    @staticmethod
    def to_json(df, compression=None):
        """Export DataFrame to JSON string with optional compression"""
        if compression == 'zip':
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                json_data = df.to_json(orient='records', indent=2)
                zf.writestr("domain_data.json", json_data)
            return zip_buffer.getvalue()
        return df.to_json(orient='records', indent=2)

    @staticmethod
    def to_excel(df, compression=None):
        """Export DataFrame to Excel bytes with optional compression"""
        excel_buffer = BytesIO()
        df.to_excel(excel_buffer, index=False)

        if compression == 'zip':
            zip_buffer = BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zf:
                zf.writestr("domain_data.xlsx", excel_buffer.getvalue())
            return zip_buffer.getvalue()
        return excel_buffer.getvalue()

    @staticmethod
    def get_filename(format, filter_term=None, min_members=None, compression=None):
        """Generate appropriate filename based on format and filters"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_name = f"zero_study_domains_{timestamp}"

        if filter_term:
            base_name += f"_filtered_{filter_term}"
        if min_members:
            base_name += f"_min_members_{min_members}"

        if compression == 'zip':
            return f"{base_name}.zip"

        return f"{base_name}.{format.lower()}"

    @staticmethod
    def should_compress(df):
        """Determine if data should be compressed based on size"""
        # Estimate DataFrame size in MB
        size_mb = df.memory_usage(deep=True).sum() / (1024 * 1024)
        return size_mb > 10  # Compress if larger than 10MB