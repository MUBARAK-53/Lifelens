"""Add experiences and memory update timestamp."""
from alembic import op
import sqlalchemy as sa

revision = "20261027_01"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("memories", sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True))
    op.create_table(
        "experiences",
        sa.Column("id", sa.Integer(), primary_key=True), sa.Column("title", sa.String(length=200)),
        sa.Column("original_filename", sa.String(length=255), nullable=False), sa.Column("relative_path", sa.String(length=500), nullable=False, unique=True),
        sa.Column("mime_type", sa.String(length=50), nullable=False), sa.Column("user_notes", sa.Text()), sa.Column("ai_description", sa.Text()),
        sa.Column("extracted_tags", sa.JSON(), nullable=False), sa.Column("analysis_status", sa.String(length=30), nullable=False, server_default="pending"), sa.Column("analysis_error", sa.Text()),
        sa.Column("captured_at", sa.DateTime(timezone=True)), sa.Column("uploaded_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False),
        sa.Column("latitude", sa.Float()), sa.Column("longitude", sa.Float()), sa.Column("location_name", sa.String(length=255)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=True),
        sa.CheckConstraint("latitude IS NULL OR (latitude >= -90 AND latitude <= 90)", name="ck_experience_latitude"), sa.CheckConstraint("longitude IS NULL OR (longitude >= -180 AND longitude <= 180)", name="ck_experience_longitude"),
    )
    for name, column in (("ix_experiences_title", "title"), ("ix_experiences_captured_at", "captured_at"), ("ix_experiences_uploaded_at", "uploaded_at"), ("ix_experiences_location_name", "location_name"), ("ix_experiences_analysis_status", "analysis_status")):
        op.create_index(name, "experiences", [column])

def downgrade() -> None:
    op.drop_table("experiences")
    op.drop_column("memories", "updated_at")
