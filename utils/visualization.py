import plotly.graph_objects as go
import math
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

class Visualizer:
    @staticmethod
    def create_network_graph(df, min_members=1):
        """Create interactive 3D network visualization with domain connections"""

        # Only show domains with members more than min_members
        df = df[df['member_count'] > min_members]

        if df.empty:
            return go.Figure()

        # Create figure with 3D scatter
        fig = go.Figure()

        # Helper function to get 3D position based on index and radius
        def get_3d_position(index, total, radius):
            """Calculate position on a spiral in 3D space"""
            phi = (1 + 5 ** 0.5) / 2  # Golden ratio for better distribution
            theta = 2 * math.pi * index * phi

            # Spherical to cartesian coordinates
            x = radius * math.sin(theta) * math.cos(index/total * math.pi)
            y = radius * math.sin(theta) * math.sin(index/total * math.pi)
            z = radius * math.cos(theta)
            return x, y, z

        # Add center point
        fig.add_trace(go.Scatter3d(
            x=[0], y=[0], z=[0],
            mode='markers',
            marker=dict(
                size=20,
                color='white',
                symbol='circle'
            ),
            name='Zero Study',
            hoverinfo='name'
        ))

        # Sort domains by member count for positioning
        df_sorted = df.sort_values('member_count', ascending=True)

        # Calculate base positions based on member count with increased scaling
        max_members = df_sorted['member_count'].max() or 1
        positions = {}

        for i, (_, domain) in enumerate(df_sorted.iterrows()):
            # Calculate radius based on member count with increased scaling and non-linear growth
            # Use power function to create more dramatic separation
            base_radius = 1
            scale_factor = 12  # Increased from 8
            power_factor = 1.5  # Adding non-linear growth
            radius = base_radius + scale_factor * (domain['member_count'] / max_members) ** power_factor

            x, y, z = get_3d_position(i, len(df_sorted), radius)
            positions[domain['name']] = (x, y, z)

            # Add domain node
            size = max(15, min(50, domain['member_count'] * 2 + 15))

            # Create explorer URL
            explorer_url = f"https://explorer.zero.tech/{domain['name'][4:]}/members"

            # Calculate color based on member count using a more dramatic scale
            # Use power function for more dramatic color transitions
            color_scale = (domain['member_count'] / max_members) ** 0.5  # Less aggressive power for colors

            # Create more vibrant colors with bounds checking
            if color_scale < 0.33:
                # Cool colors for low counts (blue to cyan)
                r = 0
                g = max(0, min(255, int(255 * (color_scale * 3))))
                b = 255
            elif color_scale < 0.66:
                # Mid range (cyan to yellow)
                r = max(0, min(255, int(255 * ((color_scale - 0.33) * 3))))
                g = 255
                b = max(0, min(255, int(255 * (1 - (color_scale - 0.33) * 3))))
            else:
                # Hot colors for high counts (yellow to red)
                r = 255
                g = max(0, min(255, int(255 * (1 - (color_scale - 0.66) * 3))))
                b = 0

            fig.add_trace(go.Scatter3d(
                x=[x], y=[y], z=[z],
                mode='markers',
                marker=dict(
                    size=size,
                    color=f'rgb({r},{g},{b})',
                    line=dict(color='white', width=1),
                    symbol='circle',
                    opacity=0.8  # Base opacity
                ),
                name=domain['name'],
                hovertemplate=(
                    f"Domain: {domain['name']}<br>"
                    f"Owner: {domain['owner']}<br>"
                    f"Members: {domain['member_count']}<br>"
                    f"<a href='{explorer_url}' target='_blank'>Join →</a>"
                    "<extra></extra>"
                ),
                hoverlabel=dict(
                    bgcolor='rgba(0,0,0,0.8)',
                    font_size=14,
                    font_family="Arial"
                )
            ))

            # Add connection line to parent domain
            if domain['is_subdomain']:
                parent_name = f"0://{domain['root_domain']}"
                if parent_name in positions:
                    px, py, pz = positions[parent_name]
                    fig.add_trace(go.Scatter3d(
                        x=[x, px], y=[y, py], z=[z, pz],
                        mode='lines',
                        line=dict(color='rgba(255,255,255,0.2)', width=1),
                        hoverinfo='none',
                        showlegend=False
                    ))
            else:
                # Connect world to center
                fig.add_trace(go.Scatter3d(
                    x=[0, x], y=[0, y], z=[0, z],
                    mode='lines',
                    line=dict(color='rgba(255,255,255,0.3)', width=1),
                    hoverinfo='none',
                    showlegend=False
                ))

        # Update layout for 3D
        fig.update_layout(
            showlegend=False,
            plot_bgcolor='black',
            paper_bgcolor='black',
            scene=dict(
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                zaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                bgcolor='black',
                # Add camera settings
                camera=dict(
                    up=dict(x=0, y=0, z=1),
                    center=dict(x=0, y=0, z=0),
                    eye=dict(x=1.5, y=1.5, z=1.5)
                ),
            ),
            margin=dict(t=0, b=0, l=0, r=0),
            height=800
        )

        return fig

    @staticmethod
    def create_member_growth_chart(df, selected_domains=None):
        """Create time series visualization of member growth using mint dates"""
        fig = go.Figure()

        # Convert mint_date strings to datetime
        df['mint_date'] = pd.to_datetime(df['mint_date'])

        if selected_domains is None:
            # Get top 5 domains by member count
            selected_domains = df.nlargest(5, 'member_count')['name'].tolist()

        # Get the date range from the data
        min_date = df['mint_date'].min()
        max_date = df['mint_date'].max()
        if not min_date or not max_date:
            min_date = datetime.now() - timedelta(days=60)
            max_date = datetime.now()

        for domain in selected_domains:
            domain_data = df[df['name'] == domain]
            if domain_data.empty:
                continue

            # Get mint date and current member count
            mint_date = domain_data.iloc[0]['mint_date']
            current_members = domain_data.iloc[0]['member_count']

            if not mint_date:
                continue

            # Create timeline from mint date to now
            dates = pd.date_range(start=mint_date, end=max_date, freq='D')

            # Calculate member growth based on mint date
            # This is a simplified model - in production you'd want to use actual historical data
            days_since_mint = (dates - mint_date).days
            member_counts = np.minimum(
                current_members,
                np.round(current_members * (days_since_mint / (days_since_mint[-1] + 1)))
            )

            # Add line plot for this domain
            fig.add_trace(go.Scatter(
                x=dates,
                y=member_counts,
                name=domain,
                mode='lines+markers',
                hovertemplate=(
                    f"Domain: {domain}<br>"
                    "Date: %{x}<br>"
                    "Members: %{y:,.0f}<br>"
                    "<extra></extra>"
                )
            ))

        # Update layout
        fig.update_layout(
            title="Domain Member Growth Over Time",
            xaxis_title="Date",
            yaxis_title="Number of Members",
            hovermode='x unified',
            showlegend=True,
            plot_bgcolor='rgba(0,0,0,0.05)',
            paper_bgcolor='rgba(0,0,0,0)',
            font=dict(color='white'),
            legend=dict(
                bgcolor='rgba(0,0,0,0.3)',
                bordercolor='rgba(255,255,255,0.2)',
                borderwidth=1
            ),
            xaxis=dict(
                showgrid=True,
                gridcolor='rgba(255,255,255,0.1)',
                tickformat='%Y-%m-%d',
                range=[min_date, max_date]
            ),
            yaxis=dict(
                showgrid=True,
                gridcolor='rgba(255,255,255,0.1)',
                tickformat=',d'
            )
        )

        return fig