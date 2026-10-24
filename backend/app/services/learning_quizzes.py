import hashlib
import json
from app.models.course import QuizAttempt
from app.models.learning import LearningQuizAttempt, LearningQuizPublication


def version(db, quiz):
    if not db.query(LearningQuizPublication).filter_by(quiz_id=quiz.id).first():
        return None
    return hashlib.sha256(json.dumps([quiz.questions, quiz.passing_score], sort_keys=True).encode()).hexdigest()


def attempts(db, user_id, quiz):
    query = db.query(QuizAttempt).filter(QuizAttempt.user_id == user_id, QuizAttempt.quiz_id == quiz.id)
    current = version(db, quiz)
    if current:
        query = query.join(LearningQuizAttempt, LearningQuizAttempt.attempt_id == QuizAttempt.id).filter(LearningQuizAttempt.version == current)
    return query
