"""Shared ERP capacity contracts supersede the former generated-window booking model."""
import pytest
from app.core.errors import Conflict, SlotTaken
from app.services import erp_catalog
from tests import test_erp_owned_slots as erp_tests

context = erp_tests.context
sessions = erp_tests.sessions
migrated = erp_tests.migrated
catalog = erp_tests.catalog
pytestmark = erp_tests.pytestmark

async def test_duplicate_patient_does_not_take_a_second_place(catalog,sessions):
    ids,client,redis,erp,_=catalog
    offer=(await erp_tests.offers(client,ids))[0]
    await erp_tests.reserve(sessions,ids,offer,erp,redis)
    with pytest.raises(Conflict,match='already have'):
        await erp_tests.reserve(sessions,ids,offer,erp,redis)
    assert (await erp_tests.offers(client,ids))[0]['remaining_places']==4

async def test_old_offer_rejected_after_erp_capacity_change(catalog,sessions):
    ids,client,redis,erp,snapshot=catalog
    offer=(await erp_tests.offers(client,ids))[0]
    snapshot['slots'][0].update(capacity=7,version=2)
    async with sessions() as session:
        await erp_catalog.sync_catalog(session,erp)
    with pytest.raises(SlotTaken,match='changed'):
        await erp_tests.reserve(sessions,ids,offer,erp,redis)

async def test_closing_slot_preserves_confirmed_reservation(catalog,sessions):
    ids,client,redis,erp,snapshot=catalog
    offer=(await erp_tests.offers(client,ids))[0]
    identifier=await erp_tests.reserve(sessions,ids,offer,erp,redis)
    snapshot['slots'][0].update(is_open=False,version=2)
    async with sessions() as session:
        await erp_catalog.sync_catalog(session,erp)
    assert await erp_tests.offers(client,ids)==[]
    detail=await client.get(f'/api/v1/appointments/{identifier}',headers=ids.headers('PATIENT'))
    assert detail.json()['status']=='CONFIRMED'
