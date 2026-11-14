"""Vietnamese synonyms for the seeded symptoms, so the AI search can match Vietnamese text.

Appends only the synonyms a symptom does not already have; admins edit them afterwards
(SCRUM-43). Symptoms are matched by their seeded English name; renamed ones are left alone.

Revision ID: 0015_vietnamese_symptom_synonyms
Revises: 0014_ai_symptom_search
"""

import sqlalchemy as sa

from alembic import op

revision = "0015_vietnamese_symptom_synonyms"
down_revision = "0014_ai_symptom_search"
branch_labels = None
depends_on = None

VI_KEYWORDS = {
    "Persistent cough": "ho,ho khan,ho có đờm,ho kéo dài,ho dai dẳng",
    "Shortness of breath": "khó thở,hụt hơi,thở gấp,thở dốc,hơi thở ngắn",
    "Chest pain": "đau ngực,tức ngực,nặng ngực,đau thắt ngực",
    "Palpitations": "hồi hộp,tim đập nhanh,đánh trống ngực,tim đập không đều",
    "Skin rash": "phát ban,nổi mẩn,nổi mề đay,mẩn đỏ,nổi mụn nước",
    "Itching": "ngứa,ngứa ngáy,ngứa da",
    "Acne": "mụn,mụn trứng cá,nổi mụn",
    "Joint pain": "đau khớp,đau khớp gối,đau đầu gối,viêm khớp,nhức khớp",
    "Morning joint stiffness": "cứng khớp buổi sáng,cứng khớp",
    "Back pain": "đau lưng,đau thắt lưng,mỏi lưng",
    "Eye discomfort": "đau mắt,đỏ mắt,cộm mắt,ngứa mắt,khó chịu ở mắt",
    "Blurred vision": "mờ mắt,mắt mờ,nhìn mờ,nhìn không rõ",
    "Sudden loss of vision": "mất thị lực đột ngột,đột nhiên không nhìn thấy,mù đột ngột",
    "Stomach pain": "đau bụng,đau dạ dày,đau bao tử,đau thượng vị",
    "Heartburn": "ợ nóng,ợ chua,trào ngược dạ dày,khó tiêu,đầy bụng,chướng bụng",
    "Diarrhea": "tiêu chảy,đi ngoài,phân lỏng,đi cầu nhiều lần",
    "Sore throat": "đau họng,viêm họng,rát họng",
    "Ear pain": "đau tai,nhức tai,ù tai",
    "Headache": "đau đầu,nhức đầu,đau nửa đầu,choáng đầu",
    "Sudden weakness or numbness on one side": (
        "yếu nửa người,tê nửa người,méo miệng,nói ngọng đột ngột,đột quỵ"
    ),
    "Fever": "sốt,sốt cao,nóng sốt,ớn lạnh",
    "Fever in a child": "trẻ bị sốt,bé bị sốt,con bị sốt,sốt ở trẻ em",
    "Fatigue": "mệt mỏi,uể oải,kiệt sức,mệt",
}


def upgrade() -> None:
    conn = op.get_bind()
    for name, extra in VI_KEYWORDS.items():
        row = conn.execute(
            sa.text("SELECT id, keywords FROM symptoms WHERE name = :name"), {"name": name}
        ).first()
        if row is None:
            continue
        current = [k.strip() for k in (row.keywords or "").split(",") if k.strip()]
        known = {k.lower() for k in current}
        merged = current + [k for k in extra.split(",") if k.lower() not in known]
        conn.execute(
            sa.text("UPDATE symptoms SET keywords = :kw WHERE id = :id"),
            {"kw": ",".join(merged)[:500], "id": row.id},
        )


def downgrade() -> None:
    pass  # synonyms are data; keeping them is harmless
