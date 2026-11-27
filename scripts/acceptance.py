"""Prueba de aceptación del integrador contra http://localhost:8080 (API real)."""
import json, sys, urllib.request, http.cookiejar

BASE = "http://localhost:8080"
ENV = dict(l.strip().split("=", 1) for l in open(sys.argv[1]) if "=" in l and not l.startswith("#"))
TELEMETRY = json.load(open(sys.argv[2]))
TOL = 2.0 * 1 / 3600  # una muestra a 2 W

def client():
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    def call(method, path, body=None):
        token = next((c.value for c in jar if c.name == "csrftoken"), "")
        req = urllib.request.Request(BASE + path, method=method,
            data=None if body is None else json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "X-CSRFToken": token, "Referer": BASE + "/"})
        try:
            with op.open(req) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")
    call("GET", "/api/auth/csrf")
    return call

results = []
def check(name, ok, detail=""):
    results.append((name, ok)); print(("PASS" if ok else "FAIL"), name, detail)

op = client()
s, _ = op("POST", "/api/auth/login", {"username": "operador_cuenca", "password": ENV["DEMO_CUENCA_PASSWORD"]})
check("login operador_cuenca", s == 200, s)

# --- Banco: prueba del jurado ---
s, st = op("POST", "/api/sites/cuenca-banco/sessions", {})
sid = st["session"]["id"]; op("POST", f"/api/sessions/{sid}/pause")
z = f"/api/sessions/{sid}/zones/carga-5v"
s, st = op("POST", z, {"on": True, "current_a": 0.40})
check("5 V × 0,40 A = 2 W", abs(st["zones"][0]["power_w"] - 2.0) < 1e-9, st["zones"][0]["power_w"])
s, st = op("POST", f"/api/sessions/{sid}/advance", {"seconds": 18})
e18 = st["session"]["energy_wh"]; check("18 s ≈ 0,010 Wh", abs(e18 - 0.010) <= TOL, e18)
op("POST", z, {"on": False}); s, st = op("POST", f"/api/sessions/{sid}/advance", {"seconds": 10})
check("10 s apagado conserva acumulado", abs(st["session"]["energy_wh"] - e18) < 1e-9 and st["session"]["total_power_w"] == 0, st["session"]["energy_wh"])
op("POST", z, {"on": True}); s, st = op("POST", f"/api/sessions/{sid}/advance", {"seconds": 18})
check("36 s efectivos ≈ 0,020 Wh", abs(st["session"]["energy_wh"] - 0.020) <= TOL, st["session"]["energy_wh"])
check("una sola alerta", len(st["alerts"]) == 1 and st["session"]["alert_fired"], len(st["alerts"]))
s, st = op("POST", f"/api/sessions/{sid}/advance", {"seconds": 5})
check("seguir consumiendo no repite alerta", len(st["alerts"]) == 1, len(st["alerts"]))
before = st["session"]
s, st = op("POST", f"/api/sessions/{sid}/next-band")
check("siguiente franja conserva Wh y elapsed_s", st["session"]["energy_wh"] == before["energy_wh"] and st["session"]["elapsed_s"] == before["elapsed_s"] and st["session"]["band"] != before["band"], (before["band"], st["session"]["band"]))
other = client(); other("POST", "/api/auth/login", {"username": "observador", "password": ENV["DEMO_OBSERVER_PASSWORD"]})
s, st2 = other("GET", "/api/sites/cuenca-banco/state")
check("refresco / segunda pestaña ven el mismo ensayo", st2["session"]["id"] == sid and st2["session"]["energy_wh"] == st["session"]["energy_wh"], st2["session"]["energy_wh"])
s, _ = other("POST", z, {"on": False}); check("observador no puede operar (403)", s == 403, s)
s, _ = op("POST", "/api/sites/puente-alto-banco/sessions", {}); check("operador Cuenca no opera Puente Alto (403)", s == 403, s)

# --- Duplicados de telemetría (sesión nueva) ---
s, st = op("POST", "/api/sites/cuenca-banco/sessions", {}); sid2 = st["session"]["id"]; op("POST", f"/api/sessions/{sid2}/pause")
# reading_id es único globalmente: se prefija con la sesión para que cada corrida use ids nuevos
batch = {**TELEMETRY, "readings": [{**r, "reading_id": f"{sid2}:{r['reading_id']}"} for r in TELEMETRY["readings"]]}
s1, r1 = op("POST", f"/api/sessions/{sid2}/readings", batch)
s2, r2 = op("POST", f"/api/sessions/{sid2}/readings", batch)
s, st = op("GET", "/api/sites/cuenca-banco/state")
exp = TELEMETRY["expected"]["energy_wh"]
check("reenviar lote no duplica Wh", abs(st["session"]["energy_wh"] - exp) < 1e-6, (st["session"]["energy_wh"], exp))

# --- Sede Cuenca y aislamiento con Puente Alto ---
pu = client(); pu("POST", "/api/auth/login", {"username": "operador_puente", "password": ENV["DEMO_PUENTE_PASSWORD"]})
s, pst = pu("POST", "/api/sites/puente-alto-sede/sessions", {}); psid = pst["session"]["id"]; pu("POST", f"/api/sessions/{psid}/pause")
pu("POST", f"/api/sessions/{psid}/zones/salon-principal", {"on": True}); s, pst = pu("POST", f"/api/sessions/{psid}/advance", {"seconds": 600})
p_before = pst["session"]["energy_wh"]
s, st = op("POST", "/api/sites/cuenca-sede/sessions", {}); vs = st["session"]["id"]; op("POST", f"/api/sessions/{vs}/pause")
op("POST", f"/api/sessions/{vs}/zones/salon-principal", {"on": True}); op("POST", f"/api/sessions/{vs}/zones/sala-reuniones", {"on": True, "intensity_pct": 100})
s, st = op("POST", f"/api/sessions/{vs}/advance", {"seconds": 1800})
zz = {x["slug"]: x for x in st["zones"]}; tot_on = st["session"]["total_power_w"]; sala_e = zz["sala-reuniones"]["energy_wh"]
op("POST", f"/api/sessions/{vs}/zones/sala-reuniones", {"on": False}); s, st = op("POST", f"/api/sessions/{vs}/advance", {"seconds": 1800})
zz = {x["slug"]: x for x in st["zones"]}
check("Cuenca: sala apagada → 0 W", zz["sala-reuniones"]["power_w"] == 0, zz["sala-reuniones"]["power_w"])
check("Cuenca: sala conserva su acumulado", abs(zz["sala-reuniones"]["energy_wh"] - sala_e) < 1e-9, sala_e)
check("Cuenca: potencia total baja y salón sigue", st["session"]["total_power_w"] < tot_on and zz["salon-principal"]["power_w"] > 0, (tot_on, st["session"]["total_power_w"]))
s, pst = pu("GET", "/api/sites/puente-alto-sede/state")
check("Puente Alto conserva su propio estado", pst["session"]["id"] == psid and pst["session"]["energy_wh"] == p_before, pst["session"]["energy_wh"])
# Prueba inversa
pu("POST", f"/api/sessions/{psid}/zones/sala-reuniones", {"on": True, "intensity_pct": 100}); pu("POST", f"/api/sessions/{psid}/advance", {"seconds": 600})
s, pst = pu("GET", "/api/sites/puente-alto-sede/state"); pz = {x["slug"]: x for x in pst["zones"]}; psala = pz["sala-reuniones"]["energy_wh"]
s, pst = pu("POST", f"/api/sessions/{psid}/zones/sala-reuniones", {"on": False}); pu("POST", f"/api/sessions/{psid}/advance", {"seconds": 600})
s, pst = pu("GET", "/api/sites/puente-alto-sede/state"); pz = {x["slug"]: x for x in pst["zones"]}
s, cst = op("GET", "/api/sites/cuenca-sede/state")
check("Inversa: Puente Alto sala 0 W, conserva Wh, salón sigue", pz["sala-reuniones"]["power_w"] == 0 and abs(pz["sala-reuniones"]["energy_wh"] - psala) < 1e-9 and pz["salon-principal"]["power_w"] > 0, psala)
check("Inversa: Cuenca no cambia", cst["session"]["id"] == vs and cst["session"]["energy_wh"] == st["session"]["energy_wh"], cst["session"]["energy_wh"])
s, cmp_ = op("GET", "/api/sites/cuenca-sede/comparison")
check("comparación: diferencia = 80 W × (dur − fin reunión)/3600", s == 200 and abs(cmp_["difference_wh"] - 80 * (cmp_["duration_s"] - 10800) / 3600) < 1e-6, cmp_.get("difference_wh"))

# Deja el banco de Cuenca con el ensayo de aceptación cerrado visible para el navegador
op("POST", "/api/sites/cuenca-banco/sessions", {})
fails = [n for n, ok in results if not ok]
print(f"\n{len(results)-len(fails)}/{len(results)} PASS"); sys.exit(1 if fails else 0)
