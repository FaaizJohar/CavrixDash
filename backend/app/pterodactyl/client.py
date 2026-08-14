from __future__ import annotations

from typing import Any

import httpx

from app.core.errors import AppError


class PterodactylClient:
    """Pterodactyl panel client.

    Application API = server provisioning/manage (Bearer app key).
    Client API     = resources, power, console, files (Bearer client key).

    Never exposes keys. All calls server-side.
    """

    def __init__(self, panel_url: str, app_api_key: str, client_api_key: str = ""):
        self.panel_url = panel_url.rstrip("/")
        self.app_api_key = app_api_key
        self.client_api_key = client_api_key

    def _app(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        return self._request(
            method, f"/api/application{path}", self.app_api_key, kwargs
        )

    def _client(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        if not self.client_api_key:
            raise AppError("Client API key not configured.", code="PTERODACTYL_CLIENT_KEY")
        return self._request(method, f"/api/client{path}", self.client_api_key, kwargs)

    def _request(self, method: str, path: str, key: str, kwargs: dict) -> httpx.Response:
        url = f"{self.panel_url}{path}"
        headers = {
            "Authorization": f"Bearer {key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        try:
            resp = httpx.request(method, url, headers=headers, timeout=30, **kwargs)
        except httpx.HTTPError as exc:
            raise AppError(
                f"Pterodactyl connection failed: {exc}", code="PTERODACTYL_UNREACHABLE", status_code=502
            )
        if resp.status_code >= 400:
            raise AppError(
                f"Pterodactyl API error ({resp.status_code}): {resp.text[:400]}",
                code="PTERODACTYL_ERROR",
                status_code=502,
            )
        return resp

    # ------------------------------------------------------------ connection
    def test(self) -> dict[str, Any]:
        resp = self._app("GET", "/nodes", params={"per_page": 1})
        data = resp.json().get("data", [])
        nodes_count = len(data)
        return {"ok": True, "nodes": nodes_count}

    def get_nodes(self) -> list[dict[str, Any]]:
        resp = self._app("GET", "/nodes", params={"per_page": 200})
        return resp.json().get("data", [])

    def get_eggs(self, nest_id: int | None = None) -> list[dict[str, Any]]:
        path = f"/nests/{nest_id}/eggs" if nest_id else "/eggs"
        resp = self._app("GET", path, params={"per_page": 200})
        return resp.json().get("data", [])

    def get_nests(self) -> list[dict[str, Any]]:
        resp = self._app("GET", "/nests", params={"per_page": 100})
        return resp.json().get("data", [])

    def get_allocations(self, node_id: int, page: int = 1, per_page: int = 200) -> list[dict[str, Any]]:
        resp = self._app("GET", f"/nodes/{node_id}/allocations", params={"per_page": per_page, "page": page})
        return resp.json().get("data", [])

    # ------------------------------------------------------------ servers (app)
    def create_server(self, *, name: str, user_id: int, egg_id: int, nest_id: int,
                      docker_image: str, startup: str, environment: dict[str, Any],
                      cpu: int, ram_mb: int, disk_mb: int, swap_mb: int = 0,
                      io: int = 500, databases: int = 0, backups: int = 0,
                      allocations: list[dict[str, Any]] | None = None, node_id: int | None = None) -> dict[str, Any]:
        limits = {
            "memory": ram_mb,
            "swap": swap_mb,
            "disk": disk_mb,
            "io": io,
            "cpu": cpu,
        }
        feature_limits = {"databases": databases, "allocations": len(allocations or [1]), "backups": backups}
        body: dict[str, Any] = {
            "name": name,
            "user": user_id,
            "egg": egg_id,
            "docker_image": docker_image,
            "startup": startup,
            "environment": environment,
            "limits": limits,
            "feature_limits": feature_limits,
        }
        if allocations:
            body["allocation"] = {"default": allocations[0]["id"], "additional": [a["id"] for a in allocations[1:]]}
        elif node_id:
            body["deploy"] = {"locations": [node_id], "dedicated_ip": False, "port_range": []}
        resp = self._app("POST", "/servers", json=body)
        attrs = resp.json().get("attributes", {})
        return attrs

    def get_server(self, server_id: str) -> dict[str, Any]:
        resp = self._app("GET", f"/servers/{server_id}")
        return resp.json().get("attributes", {})

    def suspend(self, server_id: str) -> None:
        self._app("POST", f"/servers/{server_id}/suspend")

    def unsuspend(self, server_id: str) -> None:
        self._app("POST", f"/servers/{server_id}/unsuspend")

    def delete(self, server_id: str) -> None:
        self._app("DELETE", f"/servers/{server_id}", params={"force": "true"})

    def reinstall(self, server_id: str) -> None:
        self._app("POST", f"/servers/{server_id}/reinstall")

    def create_user(self, email: str, username: str, first_name: str, last_name: str) -> dict[str, Any]:
        resp = self._app("POST", "/users", json={
            "email": email,
            "username": username,
            "first_name": first_name,
            "last_name": last_name,
        })
        return resp.json().get("attributes", {})

    def create_subuser(self, server_id: str, email: str, permissions: list[str]) -> dict[str, Any]:
        resp = self._app("POST", f"/servers/{server_id}/subusers", json={"email": email, "permissions": permissions})
        return resp.json().get("attributes", {})

    # ------------------------------------------------------------ client API
    def server_resources(self, identifier: str) -> dict[str, Any]:
        resp = self._client("GET", f"/servers/{identifier}/resources")
        return resp.json().get("attributes", {}).get("resources", {})

    def power(self, identifier: str, signal: str) -> None:
        if signal not in ("start", "stop", "restart", "kill"):
            raise AppError("Invalid power action.", code="INVALID_ACTION")
        self._client("POST", f"/servers/{identifier}/power", json={"signal": signal})

    def send_command(self, identifier: str, command: str) -> None:
        self._client("POST", f"/servers/{identifier}/command", json={"command": command})

    def websocket(self, identifier: str) -> dict[str, Any]:
        resp = self._client("GET", f"/servers/{identifier}/websocket")
        attrs = resp.json().get("attributes", {})
        return {"token": attrs.get("token", ""), "socket": attrs.get("socket", "")}

    def list_files(self, identifier: str, path: str = "/") -> list[dict[str, Any]]:
        resp = self._client("GET", f"/servers/{identifier}/files/list", params={"directory": path})
        return resp.json().get("data", [])

    def list_backups(self, identifier: str) -> list[dict[str, Any]]:
        resp = self._client("GET", f"/servers/{identifier}/backups")
        return resp.json().get("data", [])

    def restore_backup(self, identifier: str, backup_id: str) -> None:
        self._client("POST", f"/servers/{identifier}/backups/{backup_id}/restore")

    def list_schedules(self, identifier: str) -> list[dict[str, Any]]:
        resp = self._client("GET", f"/servers/{identifier}/schedules")
        return resp.json().get("data", [])

    def list_allocations(self, identifier: str) -> list[dict[str, Any]]:
        resp = self._client("GET", f"/servers/{identifier}/network/allocations")
        return resp.json().get("data", [])
