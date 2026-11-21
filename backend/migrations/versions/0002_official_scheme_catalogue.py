"""Seed official government programme portal records."""
from alembic import op
import sqlalchemy as sa

revision = "0002_official_scheme_catalogue"
down_revision = "0001_initial"
branch_labels = None
depends_on = None

def upgrade():
    schemes = sa.table(
        "government_schemes",
        sa.column("name", sa.String),
        sa.column("description", sa.Text),
        sa.column("category", sa.String),
        sa.column("department", sa.String),
        sa.column("official_portal_url", sa.String),
        sa.column("is_active", sa.Boolean),
    )
    op.bulk_insert(schemes, [
        {"name": "PM SVANidhi", "description": "Official programme portal for street-vendor support. Review current guidelines and application requirements on the government portal.", "category": "Street Vendor Support", "department": "Ministry of Housing and Urban Affairs", "official_portal_url": "https://pmsvanidhi.mohua.gov.in/", "is_active": True},
        {"name": "Pradhan Mantri MUDRA Yojana (PMMY)", "description": "Official portal for information about the MUDRA programme. Product details and lending decisions are determined by participating lenders and current official guidelines.", "category": "Credit and Enterprise", "department": "Department of Financial Services, Ministry of Finance", "official_portal_url": "https://www.mudra.org.in/", "is_active": True},
        {"name": "PM Vishwakarma", "description": "Official programme portal for eligible traditional artisans and craftspeople. Review current trade lists and application requirements on the government portal.", "category": "Artisan Support", "department": "Ministry of MSME", "official_portal_url": "https://pmvishwakarma.gov.in/", "is_active": True},
    ])

def downgrade():
    op.execute("DELETE FROM government_schemes WHERE name IN ('PM SVANidhi', 'Pradhan Mantri MUDRA Yojana (PMMY)', 'PM Vishwakarma')")
