from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_user
from app.schemas import CalibrationRequest, CalibrationResponse
from app.services import calibration

router = APIRouter(prefix="/api/calibration", tags=["calibration"])


@router.post("/train")
def train_model(db: Session = Depends(get_db), user_id: str = Depends(require_user)):
    return calibration.train(db, user_id)


@router.post("/predict", response_model=CalibrationResponse)
def predict_rating(payload: CalibrationRequest, db: Session = Depends(get_db),
                   user_id: str = Depends(require_user)):
    pred, note = calibration.predict(
        platform=payload.platform,
        official_difficulty=payload.official_difficulty,
        tags=payload.tags,
        time_taken_minutes=payload.time_taken_minutes,
        db=db,
        user_id=user_id,
    )
    return CalibrationResponse(predicted_rating=round(pred, 2), confidence_note=note)
