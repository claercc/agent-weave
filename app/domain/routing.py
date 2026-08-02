from typing import Literal,TypeAlias

Route: TypeAlias = Literal["chat", "rag", "agent"]
RoutingMode: TypeAlias = Literal["auto","chat", "rag", "agent"]