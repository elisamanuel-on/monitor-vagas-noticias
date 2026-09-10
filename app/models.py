"""Schemas Pydantic para as respostas da API (validação e documentação automática)."""
from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

EstadoVaga = Literal["por_candidatar", "candidatei_me", "resposta_recebida", "arquivada"]


class Vaga(BaseModel):
    id: str
    itjobs_id: int
    titulo: str
    empresa: str
    localizacoes: list[str] = []
    salario_min: Optional[int] = None
    salario_max: Optional[int] = None
    link: str
    publicado_em: Optional[datetime] = None
    estado: EstadoVaga = "por_candidatar"
    criado_em: datetime


class AtualizarEstadoVaga(BaseModel):
    estado: EstadoVaga


class Noticia(BaseModel):
    id: str
    titulo: str
    fonte: str
    resumo: Optional[str] = None
    link: str
    publicado_em: Optional[datetime] = None
    criado_em: datetime
