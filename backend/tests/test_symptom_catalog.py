"""Department browsing uses existing active symptom-to-specialty rules."""
import uuid

from app.models import Department, Doctor, Symptom, SymptomSpecialtyRule
from app.models.enums import DepartmentVisibility
from tests import test_scheduling_integration as fixtures

migrated = fixtures.migrated
sessions = fixtures.sessions
context = fixtures.context
pytestmark = fixtures.pytestmark


async def test_department_symptoms_respect_active_rules_and_visibility(context, sessions):
    ids, client, _ = context
    async with sessions() as session:
        doctor = await session.get(Doctor, ids.doctor)
        department_id = doctor.department_id
        symptoms = [Symptom(name=f"catalog-{uuid.uuid4().hex}", is_active=i != 2) for i in range(4)]
        session.add_all(symptoms)
        await session.flush()
        for i, symptom in enumerate(symptoms):
            session.add(SymptomSpecialtyRule(
                symptom_id=symptom.id,
                specialty_id=ids.other_specialty if i == 3 else ids.specialty,
                is_active=i != 1,
            ))
        await session.commit()
        expected_id = symptoms[0].id
    response = await client.get('/api/v1/symptoms', params={'department_id': department_id})
    assert response.status_code == 200
    assert [s['id'] for s in response.json()] == [expected_id]
    assert (await client.get('/api/v1/symptoms', params={'department_id': 0})).status_code == 422
    async with sessions() as session:
        department = await session.get(Department, department_id)
        department.visibility = DepartmentVisibility.HIDDEN
        await session.commit()
    hidden = await client.get('/api/v1/symptoms', params={'department_id': department_id})
    assert hidden.json() == []
    assert expected_id in [s['id'] for s in (await client.get('/api/v1/symptoms')).json()]
