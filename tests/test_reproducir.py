"""`reproducir`: el pipeline entero en un comando.

Se prueba el plan y el ejecutor sin correr nada de verdad: que las dependencias entre pasos
se respeten (los reportes van después de lo que leen), que los grupos caros sean opcionales
y que un paso que falla detenga todo lo que venía después.
"""

from __future__ import annotations

import pytest

from ccls import cli, reproducir


def _comandos(pasos):
    return [p.argv for p in pasos]


def test_por_defecto_corre_cpu_y_reportes_pero_no_datos_ni_gpu():
    assert {p.grupo for p in reproducir.plan()} == {"cpu", "reportes"}


def test_datos_y_gpu_son_opcionales_y_se_suman():
    assert {p.grupo for p in reproducir.plan(datos=True)} == {"datos", "cpu", "reportes"}
    assert {p.grupo for p in reproducir.plan(gpu=True)} == {"gpu", "cpu", "reportes"}
    assert {p.grupo for p in reproducir.plan(datos=True, gpu=True)} == set(reproducir.GRUPOS)


def test_el_plan_completo_respeta_el_orden_de_los_grupos():
    orden = [reproducir.GRUPOS.index(p.grupo) for p in reproducir.plan(datos=True, gpu=True)]
    assert orden == sorted(orden)


def test_cada_reporte_va_despues_de_lo_que_lee():
    cmds = _comandos(reproducir.plan(datos=True, gpu=True))
    assert cmds.index(("f2", "run")) < cmds.index(("f2", "report"))
    assert cmds.index(("f4", "run", "--barajar")) < cmds.index(("f4", "report"))
    assert cmds.index(("f5", "run", "--barajar")) < cmds.index(("f5", "report"))
    assert cmds.index(("f0", "build")) < cmds.index(("f2", "run"))
    assert cmds.index(("errores", "muestra")) < cmds.index(("errores", "report"))
    # RESULTS.md junta todo lo anterior: es lo último
    assert cmds[-1] == ("results",)


@pytest.mark.parametrize("paso", reproducir.PASOS, ids=lambda p: p.comando)
def test_todo_paso_es_un_subcomando_que_existe(paso, capsys):
    # con --help el subcomando sale con 0 si existe y con 2 si no
    profundidad = 1 if len(paso.argv) == 1 else 2
    with pytest.raises(SystemExit) as e:
        cli.main([*paso.argv[:profundidad], "--help"])
    assert e.value.code == 0


def test_falta_el_dataset_solo_importa_sin_datos(tmp_path):
    ausente = tmp_path / "dataset.jsonl"
    assert reproducir.falta_el_dataset(False, ausente)
    assert not reproducir.falta_el_dataset(True, ausente)
    ausente.write_text("{}", encoding="utf-8")
    assert not reproducir.falta_el_dataset(False, ausente)


def test_un_paso_que_falla_detiene_los_siguientes():
    llamados = []

    def main(argv):
        llamados.append(tuple(argv))
        return 3 if argv == ["f2", "run"] else 0

    mensajes: list[str] = []
    assert reproducir.correr(reproducir.plan(), main, imprimir=mensajes.append) == 3
    assert llamados[-1] == ("f2", "run")
    assert ("f2", "report") not in llamados
    assert any("falló el paso" in m for m in mensajes)


def test_si_todo_sale_bien_corre_todos_los_pasos_en_orden():
    llamados = []
    assert reproducir.correr(reproducir.plan(), lambda a: llamados.append(tuple(a)) or 0, imprimir=lambda _: None) == 0
    assert llamados == _comandos(reproducir.plan())
