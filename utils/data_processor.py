import pandas as pd
import math
import numpy as np

class DataProcessor:
    def __init__(self, data):
        self.df = pd.DataFrame(data)

    def apply_filters(self, min_members=0, max_members=None, 
                     min_payment=0, max_payment=None, 
                     payment_types=None):
        """Apply filters to the dataset"""
        filtered_df = self.df.copy()

        # Member count filter
        filtered_df = filtered_df[filtered_df['members'] >= min_members]
        if max_members:
            filtered_df = filtered_df[filtered_df['members'] <= max_members]

        # Payment amount filter
        filtered_df = filtered_df[filtered_df['payment_amount'] >= min_payment]
        if max_payment:
            filtered_df = filtered_df[filtered_df['payment_amount'] <= max_payment]

        # Payment type filter
        if payment_types:
            filtered_df = filtered_df[filtered_df['payment_type'].isin(payment_types)]

        return filtered_df

    def calculate_positions(self, df):
        """Calculate radial layout positions with hierarchical structure"""
        def get_base_domain(domain):
            return '.'.join(domain.split('.')[-2:])

        def is_subdomain(domain):
            parts = domain.split('.')
            return len(parts) > 2

        # Add domain type and base domain columns
        df = df.copy()
        df['base_domain'] = df['subdomain'].apply(get_base_domain)
        df['is_subdomain'] = df['subdomain'].apply(is_subdomain)

        # Calculate positions
        positions = []
        domain_angles = {}
        base_domains = df['base_domain'].unique()

        # First, position primary domains
        for i, domain in enumerate(base_domains):
            angle = 2 * math.pi * (i / len(base_domains))
            domain_angles[domain] = angle

        for i, row in df.iterrows():
            base_angle = domain_angles[row['base_domain']]

            if row['is_subdomain']:
                # Subdomains: larger radius based on member count
                radius = 300 + (row['members'] * 2)  # Farther out based on members
                # Add small variation to angle for subdomains
                angle = base_angle + 0.2 * (hash(row['subdomain']) % 10 - 5) / 10
            else:
                # Primary domains: smaller base radius
                radius = 200 + (row['members'])  # Closer to center
                angle = base_angle

            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            positions.append((x, y))

        df['x'] = [pos[0] for pos in positions]
        df['y'] = [pos[1] for pos in positions]

        return df