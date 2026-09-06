from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.certification import Certification
from app.models.education import Education
from app.models.project import Project
from app.models.skill_profile import SkillProfileItem
from app.models.work_experience import WorkExperience
from app.schemas.profile_sections import (
    CertificationCreate,
    CertificationOut,
    CertificationUpdate,
    EducationCreate,
    EducationOut,
    EducationUpdate,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    WorkExperienceCreate,
    WorkExperienceOut,
    WorkExperienceUpdate,
)
from app.schemas.skill_profile import SkillProfileItemCreate, SkillProfileItemOut, SkillProfileItemUpdate

router = APIRouter(prefix="/api/profile", tags=["profile"])


# ---------------------------------------------------------------------------
# Skills (skill_profile_items is also the ONLY source CV tailoring may draw
# from -- see app/services/tailoring.py's non-negotiable no-fabrication rule)
# ---------------------------------------------------------------------------


@router.get("/skills", response_model=list[SkillProfileItemOut])
def list_skills(include_inactive: bool = True, db: Session = Depends(get_db)):
    stmt = select(SkillProfileItem).order_by(SkillProfileItem.sort_order, SkillProfileItem.skill_name)
    if not include_inactive:
        stmt = stmt.where(SkillProfileItem.is_active.is_(True))
    return db.execute(stmt).scalars().all()


@router.post("/skills", response_model=SkillProfileItemOut)
def create_skill(payload: SkillProfileItemCreate, db: Session = Depends(get_db)):
    """New entries start with embedding=NULL -- RAG retrieval (pipeline/rag.py,
    app/services/rag.py) falls back to the full active list until the backfill
    job re-runs, so this shows up in tailoring/matching immediately either way.
    """
    item = SkillProfileItem(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/skills/{skill_id}", response_model=SkillProfileItemOut)
def update_skill(skill_id: int, payload: SkillProfileItemUpdate, db: Session = Depends(get_db)):
    item = db.get(SkillProfileItem, skill_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Skill not found")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        setattr(item, field, value)

    # A changed name/description makes the existing embedding stale -- clear it so
    # RAG falls back to the full list rather than ranking on outdated text until
    # the next backfill run.
    if "skill_name" in updates or "evidence_bullet" in updates:
        item.embedding = None

    db.commit()
    db.refresh(item)
    return item


@router.delete("/skills/{skill_id}")
def delete_skill(skill_id: int, db: Session = Depends(get_db)):
    item = db.get(SkillProfileItem, skill_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Skill not found")
    db.delete(item)
    db.commit()
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Education
# ---------------------------------------------------------------------------


@router.get("/education", response_model=list[EducationOut])
def list_education(db: Session = Depends(get_db)):
    stmt = select(Education).order_by(Education.sort_order, Education.start_date.desc().nullslast())
    return db.execute(stmt).scalars().all()


@router.post("/education", response_model=EducationOut)
def create_education(payload: EducationCreate, db: Session = Depends(get_db)):
    item = Education(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/education/{item_id}", response_model=EducationOut)
def update_education(item_id: int, payload: EducationUpdate, db: Session = Depends(get_db)):
    item = db.get(Education, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Education entry not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/education/{item_id}")
def delete_education(item_id: int, db: Session = Depends(get_db)):
    item = db.get(Education, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Education entry not found")
    db.delete(item)
    db.commit()
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Work experience
# ---------------------------------------------------------------------------


@router.get("/experience", response_model=list[WorkExperienceOut])
def list_experience(db: Session = Depends(get_db)):
    stmt = select(WorkExperience).order_by(WorkExperience.sort_order, WorkExperience.start_date.desc().nullslast())
    return db.execute(stmt).scalars().all()


@router.post("/experience", response_model=WorkExperienceOut)
def create_experience(payload: WorkExperienceCreate, db: Session = Depends(get_db)):
    item = WorkExperience(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/experience/{item_id}", response_model=WorkExperienceOut)
def update_experience(item_id: int, payload: WorkExperienceUpdate, db: Session = Depends(get_db)):
    item = db.get(WorkExperience, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Work experience entry not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/experience/{item_id}")
def delete_experience(item_id: int, db: Session = Depends(get_db)):
    item = db.get(WorkExperience, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Work experience entry not found")
    db.delete(item)
    db.commit()
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Projects
# ---------------------------------------------------------------------------


@router.get("/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    stmt = select(Project).order_by(Project.sort_order, Project.start_date.desc().nullslast())
    return db.execute(stmt).scalars().all()


@router.post("/projects", response_model=ProjectOut)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    item = Project(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/projects/{item_id}", response_model=ProjectOut)
def update_project(item_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)):
    item = db.get(Project, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Project not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/projects/{item_id}")
def delete_project(item_id: int, db: Session = Depends(get_db)):
    item = db.get(Project, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(item)
    db.commit()
    return {"deleted": True}


# ---------------------------------------------------------------------------
# Certifications & awards
# ---------------------------------------------------------------------------


@router.get("/certifications", response_model=list[CertificationOut])
def list_certifications(db: Session = Depends(get_db)):
    stmt = select(Certification).order_by(Certification.sort_order, Certification.issue_date.desc().nullslast())
    return db.execute(stmt).scalars().all()


@router.post("/certifications", response_model=CertificationOut)
def create_certification(payload: CertificationCreate, db: Session = Depends(get_db)):
    item = Certification(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/certifications/{item_id}", response_model=CertificationOut)
def update_certification(item_id: int, payload: CertificationUpdate, db: Session = Depends(get_db)):
    item = db.get(Certification, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Certification not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/certifications/{item_id}")
def delete_certification(item_id: int, db: Session = Depends(get_db)):
    item = db.get(Certification, item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Certification not found")
    db.delete(item)
    db.commit()
    return {"deleted": True}
