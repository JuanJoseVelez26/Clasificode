from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class CandidateOut:
    hs_code: str
    title: str
    confidence: float
    rank: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            'hs_code': self.hs_code,
            'title': self.title,
            'confidence': self.confidence,
            'rank': self.rank,
        }


@dataclass
class ClassificationResponse:
    case_id: int
    hs6: str
    national_code: str
    title: str
    rgi_applied: List[str]
    legal_notes: List[int]
    sources: List[int]
    rationale: str
    candidates: List[CandidateOut]

    def to_dict(self) -> Dict[str, Any]:
        return {
            'case_id': self.case_id,
            'hs6': self.hs6,
            'national_code': self.national_code,
            'title': self.title,
            'rgi_applied': self.rgi_applied or [],
            'legal_notes': self.legal_notes or [],
            'sources': self.sources or [],
            'rationale': self.rationale or '',
            'candidates': [c.to_dict() for c in self.candidates or []],
        }
