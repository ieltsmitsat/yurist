"""Tests for FastAPI endpoints: Health, Webhook validation, and CRM."""

from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.api.main import app
from app.db.base import Base
from app.db.models.appointment import Appointment
from app.db.models.attachment import Attachment
from app.db.models.chat_message import ChatMessage
from app.db.models.inquiry import Inquiry
from app.db.models.service import Service
from app.db.models.sos import SOSRequest
from app.db.models.system_access import SystemAccess
from app.db.models.transaction import Transaction
from app.db.models.user import User
from app.db.session import get_db_session

test_engine = create_async_engine(
    "sqlite+aiosqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False,
)
TestingSessionLocal = async_sessionmaker(
    bind=test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db():
    async with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db_session] = override_get_db


@pytest.fixture(autouse=True)
async def setup_test_db():
    async with test_engine.begin() as conn:
        tables = [
            User.__table__,
            Service.__table__,
            Inquiry.__table__,
            Appointment.__table__,
            Attachment.__table__,
            Transaction.__table__,
            SOSRequest.__table__,
            ChatMessage.__table__,
            SystemAccess.__table__,
        ]
        await conn.run_sync(Base.metadata.create_all, tables=tables)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all, tables=tables)


@pytest.mark.asyncio
async def test_health_check_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "Yurist" in data["project"]


@pytest.mark.asyncio
async def test_webhook_secret_token_validation():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Invalid secret token
        response = await client.post(
            "/api/v1/webhook",
            json={"update_id": 123},
            headers={"X-Telegram-Bot-Api-Secret-Token": "wrong_secret"},
        )
        assert response.status_code == 403


@pytest.mark.asyncio
async def test_crm_leads_and_approval():
    # 1. Seed user and inquiry
    async with TestingSessionLocal() as session:
        user = User(
            telegram_id=999888,
            full_name="CRM Test User",
            phone_number="+998901112233",
            lead_status="verified_lead",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        inquiry = Inquiry(
            user_id=user.id,
            question_text="Mehnat nizosi bo'yicha",
            risk_level="high",
            risk_score=75,
            ai_draft_response="Dastlabki AI loyihasi",
        )
        session.add(inquiry)
        await session.commit()
        await session.refresh(inquiry)
        inquiry_id = inquiry.id

    # 2. Test CRM endpoints
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get leads
        leads_res = await client.get("/api/v1/crm/leads")
        assert leads_res.status_code == 200
        leads = leads_res.json()
        assert len(leads) >= 1
        assert leads[0]["full_name"] == "CRM Test User"

        # Get inquiries
        inq_res = await client.get("/api/v1/crm/inquiries")
        assert inq_res.status_code == 200
        inquiries = inq_res.json()
        assert len(inquiries) >= 1
        assert inquiries[0]["risk_level"] == "high"

        # Approve inquiry by lawyer
        approve_res = await client.post(
            f"/api/v1/crm/inquiries/{inquiry_id}/approve",
            json={
                "final_response": "Advokat tomonidan tahrirlangan va tasdiqlangan javob.",
                "lawyer_id": 777,
            },
        )
        assert approve_res.status_code == 200
        assert approve_res.json()["ok"] is True
        assert approve_res.json()["status"] == "approved"


@pytest.mark.asyncio
async def test_dashboard_stats_and_analytics():
    # 1. Seed users, inquiries, transactions
    async with TestingSessionLocal() as session:
        u1 = User(
            telegram_id=111,
            full_name="User One",
            phone_number="+998901111111",
            lead_status="closed_won",
            is_subscribed=True,
        )
        session.add(u1)
        await session.commit()
        await session.refresh(u1)

        u2 = User(
            telegram_id=222,
            full_name="User Two",
            phone_number="+998902222222",
            lead_status="new",
            referred_by_id=u1.id,
        )
        session.add(u2)
        await session.commit()
        await session.refresh(u2)

        inq = Inquiry(
            user_id=u1.id,
            question_text="Mulk huquqi bo'yicha",
            risk_level="high",
            risk_score=80,
        )
        session.add(inq)

        tx = Transaction(
            user_id=u1.id,
            amount=Decimal("150000.00"),
            payment_method="p2p_card",
            payment_status="completed",
        )
        session.add(tx)
        await session.commit()

    # 2. Query dashboard endpoints
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Stats
        stats_res = await client.get("/api/v1/dashboard/stats")
        assert stats_res.status_code == 200
        stats = stats_res.json()
        assert stats["total_users"] == 2
        assert stats["total_inquiries"] == 1
        assert stats["total_revenue"] == 150000.0
        assert stats["referred_users"] == 1
        assert stats["subscribers"] == 1

        # Pipeline
        pipe_res = await client.get("/api/v1/dashboard/pipeline")
        assert pipe_res.status_code == 200
        pipe = pipe_res.json()
        assert len(pipe) >= 2

        # Risk breakdown
        risk_res = await client.get("/api/v1/dashboard/risk-breakdown")
        assert risk_res.status_code == 200
        risks = risk_res.json()
        assert any(r["level"] == "high" for r in risks)

        # Referral stats
        ref_res = await client.get("/api/v1/dashboard/referral-stats")
        assert ref_res.status_code == 200
        ref_data = ref_res.json()
        assert ref_data["total_referred"] == 1
        assert ref_data["verified_referred"] == 1
        assert len(ref_data["top_referrers"]) == 1


@pytest.mark.asyncio
async def test_services_crud_api():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Create service
        create_res = await client.post(
            "/api/v1/services",
            json={
                "title_uz": "Yangi xizmat",
                "title_ru": "Новая услуга",
                "price": 200000.0,
                "service_type": "consultation",
                "is_active": True,
            },
        )
        assert create_res.status_code == 201
        srv_id = create_res.json()["id"]

        # List services
        list_res = await client.get("/api/v1/services")
        assert list_res.status_code == 200
        services = list_res.json()
        assert len(services) == 1
        assert services[0]["title_uz"] == "Yangi xizmat"

        # Update service
        update_res = await client.put(
            f"/api/v1/services/{srv_id}",
            json={"price": 250000.0},
        )
        assert update_res.status_code == 200

        # Delete service (soft delete)
        del_res = await client.delete(f"/api/v1/services/{srv_id}")
        assert del_res.status_code == 200

        list_res2 = await client.get("/api/v1/services")
        assert list_res2.json()[0]["is_active"] is False


@pytest.mark.asyncio
async def test_transactions_api():
    async with TestingSessionLocal() as session:
        user = User(
            telegram_id=333,
            full_name="Payer User",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        tx = Transaction(
            user_id=user.id,
            amount=Decimal("300000.00"),
            payment_method="telegram_stars",
            payment_status="pending",
        )
        session.add(tx)
        await session.commit()
        await session.refresh(tx)
        tx_id = tx.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # List transactions
        tx_res = await client.get("/api/v1/transactions")
        assert tx_res.status_code == 200
        transactions = tx_res.json()
        assert len(transactions) == 1
        assert transactions[0]["user_name"] == "Payer User"

        # Update status
        upd_res = await client.put(
            f"/api/v1/transactions/{tx_id}/status",
            json={"payment_status": "completed", "transaction_ref": "STARS_12345"},
        )
        assert upd_res.status_code == 200
        assert upd_res.json()["status"] == "completed"


@pytest.mark.asyncio
async def test_crm_lead_status_update():
    async with TestingSessionLocal() as session:
        user = User(
            telegram_id=444,
            full_name="Pipeline Lead",
            lead_status="new",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        user_id = user.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get lead detail
        detail_res = await client.get(f"/api/v1/crm/leads/{user_id}")
        assert detail_res.status_code == 200
        assert detail_res.json()["lead_status"] == "new"

        # Update status to proposal_sent
        status_res = await client.put(
            f"/api/v1/crm/leads/{user_id}/status",
            json={"lead_status": "proposal_sent"},
        )
        assert status_res.status_code == 200
        assert status_res.json()["lead_status"] == "proposal_sent"


@pytest.mark.asyncio
async def test_chat_endpoints():
    from app.services.chat_service import ChatService
    
    # 1. Seed user and messages
    async with TestingSessionLocal() as session:
        user = User(
            telegram_id=5555,
            full_name="Chat Test User",
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)

        # Log a few messages
        await ChatService.log_message(session, user.id, user.telegram_id, "user", "Salom, bot!")
        await ChatService.log_message(session, user.id, user.telegram_id, "bot", "Assalomu alaykum!")

    # 2. Test Chat API
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # Get dialogs list
        dialogs_res = await client.get("/api/v1/chats")
        assert dialogs_res.status_code == 200
        dialogs = dialogs_res.json()
        assert len(dialogs) >= 1
        # It's possible there are other users in DB from previous tests, so let's find our user
        dialog = next(d for d in dialogs if d["full_name"] == "Chat Test User")
        assert dialog["total_messages"] == 2

        # Get messages for the user
        msgs_res = await client.get(f"/api/v1/chats/{user.id}")
        assert msgs_res.status_code == 200
        msgs = msgs_res.json()
        assert len(msgs) == 2
        assert msgs[0]["sender_type"] == "user"
        assert msgs[1]["sender_type"] == "bot"

        # Send lawyer reply
        from unittest.mock import AsyncMock, patch
        
        with patch("app.bot.bot_instance.bot.send_message", new_callable=AsyncMock) as mock_send:
            mock_send.return_value.message_id = 9999
            send_res = await client.post(
                f"/api/v1/chats/{user.id}/send",
                json={"text": "Bu advokatdan javob!"}
            )
            assert send_res.status_code == 201
            assert send_res.json()["text"] == "Bu advokatdan javob!"
            assert send_res.json()["sender_type"] == "lawyer"
            mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_system_access_crud_api():
    """Test CRUD operations for System Access (lawyers, groups, admins)."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # 1. Create a lawyer
        res = await client.post(
            "/api/v1/settings/access",
            json={
                "telegram_id": 555666777,
                "role": "lawyer",
                "name": "Advokat Jamshid",
                "description": "Bosh yurist konsultant",
                "is_active": True,
            },
        )
        assert res.status_code == 201
        lawyer_data = res.json()
        assert lawyer_data["telegram_id"] == 555666777
        assert lawyer_data["role"] == "lawyer"
        assert lawyer_data["name"] == "Advokat Jamshid"
        lawyer_id = lawyer_data["id"]

        # 2. Create a group
        res_group = await client.post(
            "/api/v1/settings/access",
            json={
                "telegram_id": -1001987654321,
                "role": "group",
                "name": "Lidlar guruhi",
                "description": "Yangi arizalar guruhi",
                "is_active": True,
                "lead_topic_id": 12,
                "contact_topic_id": 14,
                "payment_topic_id": 16,
            },
        )
        assert res_group.status_code == 201
        group_data = res_group.json()
        assert group_data["role"] == "group"
        assert group_data["lead_topic_id"] == 12
        assert group_data["contact_topic_id"] == 14
        assert group_data["payment_topic_id"] == 16

        # 3. List all access entries
        res_list = await client.get("/api/v1/settings/access")
        assert res_list.status_code == 200
        items = res_list.json()
        assert len(items) >= 2

        # 4. Filter by role
        res_lawyers = await client.get("/api/v1/settings/access?role=lawyer")
        assert res_lawyers.status_code == 200
        lawyers_only = res_lawyers.json()
        assert all(item["role"] == "lawyer" for item in lawyers_only)

        # 5. Update lawyer
        res_update = await client.put(
            f"/api/v1/settings/access/{lawyer_id}",
            json={
                "name": "Advokat Jamshid (Bosh)",
                "description": "Yangilangan tavsif",
            },
        )
        assert res_update.status_code == 200
        assert res_update.json()["name"] == "Advokat Jamshid (Bosh)"
        assert res_update.json()["description"] == "Yangilangan tavsif"

        # 6. Delete lawyer
        res_del = await client.delete(f"/api/v1/settings/access/{lawyer_id}")
        assert res_del.status_code == 200
        assert res_del.json()["ok"] is True

        # Verify deleted
        res_get_del = await client.get("/api/v1/settings/access?role=lawyer")
        assert not any(i["id"] == lawyer_id for i in res_get_del.json())
