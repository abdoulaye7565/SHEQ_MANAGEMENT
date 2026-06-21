from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class Employee:
    id_employe: int
    nom: str
    prenom: str
    nom_complet: str
    type_employe: str
    site_id: int
    site: str
    fonction: str
    shift_code: str
    statut: str = "actif"
    groupe: str = ""
    numero_badge: str = ""

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Employee":
        return cls(
            id_employe=int(row["id_employe"]),
            nom=str(row.get("nom") or ""),
            prenom=str(row.get("prenom") or ""),
            nom_complet=str(row.get("nom_complet") or ""),
            type_employe=str(row.get("type_employe") or ""),
            site_id=int(row.get("site_id") or 0),
            site=str(row.get("site") or ""),
            fonction=str(row.get("fonction") or ""),
            shift_code=str(row.get("shift_code") or ""),
            statut=str(row.get("statut") or "actif"),
            groupe=str(row.get("groupe") or ""),
            numero_badge=str(row.get("numero_badge") or ""),
        )

    def asdict(self) -> dict[str, Any]:
        return asdict(self)

    @property
    def display_name(self) -> str:
        parts = [self.nom, self.prenom]
        return " ".join(p for p in parts if p) or self.nom_complet


@dataclass
class PresenceRecord:
    id_presence: int
    employe_id: int
    date_presence: str
    statut_presence: str
    heure_entree: str | None = None
    heure_sortie: str | None = None
    heures_travaillees: float | None = None
    shift_id: int | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "PresenceRecord":
        return cls(
            id_presence=int(row["id_presence"]),
            employe_id=int(row["employe_id"]),
            date_presence=str(row["date_presence"]),
            statut_presence=str(row["statut_presence"]),
            heure_entree=str(row["heure_entree"]) if row.get("heure_entree") else None,
            heure_sortie=str(row["heure_sortie"]) if row.get("heure_sortie") else None,
            heures_travaillees=float(row["heures_travaillees"]) if row.get("heures_travaillees") is not None else None,
            shift_id=int(row["shift_id"]) if row.get("shift_id") else None,
        )

    def asdict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Alert:
    alert_id: str
    source_key: str
    source: str
    type_alerte: str
    message: str
    niveau: str
    statut: str
    date_creation: str
    reference_id: int | None = None
    reference_label: str = ""
    action_hint: str = ""

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Alert":
        return cls(
            alert_id=str(row["alert_id"]),
            source_key=str(row["source_key"]),
            source=str(row["source"]),
            type_alerte=str(row["type_alerte"]),
            message=str(row["message"]),
            niveau=str(row["niveau"]),
            statut=str(row["statut"]),
            date_creation=str(row["date_creation"]),
            reference_id=int(row["reference_id"]) if row.get("reference_id") is not None else None,
            reference_label=str(row.get("reference_label") or ""),
            action_hint=str(row.get("action_hint") or ""),
        )

    def asdict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class Formation:
    id_formation: int
    employe_id: int
    type_formation_id: int
    type_formation: str
    date_formation: str
    date_expiration: str | None
    statut: str
    organisme: str = ""
    score: float | None = None

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> "Formation":
        return cls(
            id_formation=int(row["id_formation"]),
            employe_id=int(row["employe_id"]),
            type_formation_id=int(row.get("type_formation_id") or 0),
            type_formation=str(row.get("type_formation") or ""),
            date_formation=str(row["date_formation"]),
            date_expiration=str(row["date_expiration"]) if row.get("date_expiration") else None,
            statut=str(row.get("statut") or "valide"),
            organisme=str(row.get("organisme") or ""),
            score=float(row["score"]) if row.get("score") is not None else None,
        )

    def asdict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class AppUser:
    id_user: int
    username: str
    role: str
    statut: str = "actif"
    modules: list[str] = field(default_factory=list)

    @classmethod
    def from_row(cls, row: dict[str, Any], modules: list[str] | None = None) -> "AppUser":
        return cls(
            id_user=int(row["id_user"]),
            username=str(row["username"]),
            role=str(row.get("role") or ""),
            statut=str(row.get("statut") or "actif"),
            modules=list(modules or []),
        )

    def asdict(self) -> dict[str, Any]:
        return asdict(self)

    def can_access(self, module: str) -> bool:
        return module in self.modules
