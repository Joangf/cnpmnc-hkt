"""Public discovery endpoints (FRD 4.3, 4.6). No authentication required."""

from typing import Annotated

from fastapi import APIRouter, Query

from app.api import presenters
from app.api.deps import PageDep, SessionDep
from app.core.errors import NotFound
from app.models.enums import FacilityType
from app.repositories import directory as directory_repo
from app.repositories import reviews as review_repo
from app.schemas.common import Page, error_responses
from app.schemas.directory import (
    AppointmentTypeOut,
    DoctorDetail,
    DoctorSummary,
    HospitalDetail,
    HospitalSummary,
    SpecialtyOut,
)
from app.schemas.reviews import ReviewPublic
from app.services import policies

router = APIRouter(tags=["directory"])

SearchText = Annotated[str | None, Query(max_length=100)]


@router.get("/specialties", response_model=list[SpecialtyOut], operation_id="listSpecialties")
async def list_specialties(session: SessionDep) -> list[SpecialtyOut]:
    return [SpecialtyOut.model_validate(s) for s in await directory_repo.list_specialties(session)]


@router.get("/hospitals", response_model=Page[HospitalSummary], operation_id="listHospitals")
async def list_hospitals(
    session: SessionDep,
    paging: PageDep,
    q: SearchText = None,
    city: SearchText = None,
    specialty_id: int | None = None,
    facility_type: FacilityType | None = None,
) -> Page[HospitalSummary]:
    items, total = await directory_repo.list_hospitals(
        session,
        q=q,
        city=city,
        specialty_id=specialty_id,
        facility_type=facility_type,
        page=paging.page,
        page_size=paging.page_size,
    )
    return Page[HospitalSummary](
        items=[presenters.hospital_summary(h) for h in items],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
    )


@router.get(
    "/hospitals/{hospital_id}",
    response_model=HospitalDetail,
    operation_id="getHospital",
    responses=error_responses(404),
)
async def get_hospital(hospital_id: int, session: SessionDep) -> HospitalDetail:
    hospital = await directory_repo.get_hospital(session, hospital_id)
    if hospital is None or not hospital.is_active:
        raise NotFound("Hospital not found.")
    return presenters.hospital_detail(hospital)


@router.get("/doctors", response_model=Page[DoctorSummary], operation_id="listDoctors")
async def list_doctors(
    session: SessionDep,
    paging: PageDep,
    q: SearchText = None,
    hospital_id: int | None = None,
    department_id: int | None = None,
    specialty_id: int | None = None,
) -> Page[DoctorSummary]:
    items, total = await directory_repo.list_doctors(
        session,
        q=q,
        hospital_id=hospital_id,
        department_id=department_id,
        specialty_id=specialty_id,
        page=paging.page,
        page_size=paging.page_size,
    )
    return Page[DoctorSummary](
        items=[presenters.doctor_summary(d) for d in items],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
    )


@router.get(
    "/doctors/{doctor_id}",
    response_model=DoctorDetail,
    operation_id="getDoctor",
    responses=error_responses(404),
)
async def get_doctor(doctor_id: int, session: SessionDep) -> DoctorDetail:
    doctor = await directory_repo.get_doctor(session, doctor_id)
    if doctor is None or not policies.doctor_is_published(doctor):
        raise NotFound("Doctor not found.")
    return presenters.doctor_detail(doctor)


@router.get(
    "/doctors/{doctor_id}/appointment-types",
    response_model=list[AppointmentTypeOut],
    operation_id="listDoctorAppointmentTypes",
    responses=error_responses(404),
)
async def list_doctor_appointment_types(
    doctor_id: int, session: SessionDep
) -> list[AppointmentTypeOut]:
    doctor = await directory_repo.get_doctor(session, doctor_id)
    if doctor is None or not policies.doctor_is_published(doctor):
        raise NotFound("Doctor not found.")
    types = await directory_repo.list_appointment_types_for_doctor(session, doctor)
    return [presenters.appointment_type_out(t, doctor) for t in types]


@router.get(
    "/doctors/{doctor_id}/reviews",
    response_model=Page[ReviewPublic],
    operation_id="listDoctorReviews",
    tags=["reviews"],
)
async def list_doctor_reviews(
    doctor_id: int, session: SessionDep, paging: PageDep
) -> Page[ReviewPublic]:
    items, total = await review_repo.list_published_for_doctor(
        session, doctor_id, paging.page, paging.page_size
    )
    return Page[ReviewPublic](
        items=[presenters.review_public(r) for r in items],
        total=total,
        page=paging.page,
        page_size=paging.page_size,
    )
