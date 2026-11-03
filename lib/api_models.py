"""Pydantic models for SON REST API responses."""

from typing import Optional
from pydantic import BaseModel


class TenantOut(BaseModel):
    tenant_id: int
    user_fullname: str
    address: Optional[str] = None
    user_active: Optional[bool] = None
    user_balance: Optional[float] = None
    estate_id: Optional[int] = None
    eah_owner_fullname: Optional[str] = None
    tags: Optional[str] = None


class OperationOut(BaseModel):
    tenant_id: Optional[int] = None
    tenant_name: Optional[str] = None
    type: Optional[str] = None
    date: Optional[str] = None
    income: Optional[float] = None
    expense: Optional[float] = None
    balance: Optional[float] = None
    document: Optional[str] = None
    pdf_url: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None


class LiabilityOut(BaseModel):
    tenant_id: Optional[int] = None
    tenant_name: Optional[str] = None
    item_name: Optional[str] = None
    amount_before_discount: Optional[float] = None
    amount_after_discount: Optional[float] = None
    total_discount: Optional[float] = None
    discount_details: Optional[str] = None
    billing_frequency: Optional[str] = None
    period: Optional[str] = None


class InsuranceOut(BaseModel):
    tenant_id: Optional[int] = None
    tenant_name: Optional[str] = None
    id: Optional[int] = None
    company: Optional[str] = None
    policy_number: Optional[str] = None
    status: Optional[int] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    estate_id: Optional[int] = None
    room_id: Optional[int] = None
    created_at: Optional[str] = None


class FinanceOut(BaseModel):
    type: Optional[str] = None
    date: Optional[str] = None
    payment: Optional[float] = None
    charge: Optional[float] = None
    balance: Optional[float] = None
    document: Optional[str] = None
    pdf_url: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None


class CostDocumentOut(BaseModel):
    estate_id: Optional[int] = None
    date_added: Optional[str] = None
    sale_date: Optional[str] = None
    seller: Optional[str] = None
    is_payout: Optional[bool] = None
    number: Optional[str] = None
    amount: Optional[float] = None
    payment_deadline: Optional[str] = None
    payment_date: Optional[str] = None
    download_zip_url: Optional[str] = None
    cost_document_id: Optional[int] = None
    pdf_url: Optional[str] = None


class ArtifactLink(BaseModel):
    relative: str
    absolute: str


class LatestDownloadResult(BaseModel):
    kind: str
    status: str
    path: Optional[str] = None
    url: Optional[ArtifactLink] = None
    error: Optional[str] = None


class LatestOut(BaseModel):
    income_invoice: Optional[OperationOut] = None
    cost_invoice: Optional[FinanceOut] = None
    payout: Optional[CostDocumentOut] = None
    payment: Optional[OperationOut] = None
    warnings: list[str] = []
    last_document_date: Optional[str] = None


class LatestDownloadOut(LatestOut):
    downloads: dict[str, LatestDownloadResult] = {}
    state_updated: bool = False


class LatestDownloadRequest(BaseModel):
    types: Optional[list[str]] = None
    force: bool = False


class EstateOut(BaseModel):
    address: Optional[str] = None
    estate_is_under_renovation: Optional[bool] = None
    estate_manage_type: Optional[int] = None
    estate_id: Optional[int] = None
    tags: Optional[str] = None
    estate_details: Optional[str] = None
    estate_rental_type: Optional[int] = None
    rooms_accommodation: Optional[str] = None
    free_rooms_count: Optional[int] = None


class LiveOut(BaseModel):
    status: str


class HealthOut(BaseModel):
    status: str
    son_connected: bool
