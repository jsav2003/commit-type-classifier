# Análisis de errores

Generado por `python -m ccls errores report` desde `data/processed/errores_muestra.csv` y `data/processed/errores_causas.csv`. **No se edita a mano:** las causas se cambian en el CSV. Diseño en `DESIGN.md` §7.6.

## Qué se revisó

El modelo es `clasico_lr_balanceado`, el clásico de referencia, en la partición por repositorio: cada commit lo predice un modelo entrenado sin ver su repositorio. Se equivoca en **2333 de 10000 commits (23,3%)**. De esos se revisaron 10 por repositorio, tomados por orden de hash con una semilla fija (`src/ccls/errores.py`).

**Limitación.** La muestra pesa igual a todos los repos, así que dice qué tipo de error hay en cada proyecto y no cuántos hay en total: las proporciones de abajo no son la tasa de cada causa en el dataset. Los errores de CodeBERT y de la red desde cero no se revisan: sus corridas guardan métricas y matrices de confusión, no la predicción de cada commit.

| repositorio | commits | errores | tasa de error |
|---|---:|---:|---:|
| angular/angular-cli | 2000 | 594 | 29,7% |
| nuxt/nuxt | 2000 | 453 | 22,7% |
| sveltejs/svelte | 2000 | 359 | 17,9% |
| vitejs/vite | 2000 | 418 | 20,9% |
| vitest-dev/vitest | 2000 | 509 | 25,4% |

Errores por par (verdad → predicción), sobre **todos** los errores:

| verdad → predicción | errores | del total |
|---|---:|---:|
| `docs` → `feat` | 63 | 2,7% |
| `docs` → `fix` | 89 | 3,8% |
| `docs` → `refactor` | 26 | 1,1% |
| `feat` → `docs` | 38 | 1,6% |
| `feat` → `fix` | 414 | 17,7% |
| `feat` → `refactor` | 156 | 6,7% |
| `fix` → `docs` | 87 | 3,7% |
| `fix` → `feat` | 636 | 27,3% |

## Las causas

Son las de DESIGN.md §7.6 más una: `fuera_de_clases`, que el diseño no tenía. La F3 midió que en los repos sin convención el 31% de los commits no es ninguna de las cuatro clases y el clasificador no puede decir "ninguna"; sin esta causa esos errores caerían en `error_modelo` y lo inflarían.

| causa | qué significa |
|---|---|
| `etiqueta_autor` | La etiqueta que puso el autor es discutible: lo que predijo el modelo se defiende. |
| `mixto` | El commit hace de verdad varias cosas de peso; ninguna etiqueta única es correcta. |
| `mensaje_inutil` | El mensaje no dice qué se hizo (`wip`, `update`, `changes`), así que no hay de dónde aprender. |
| `fuera_de_clases` | No es ninguna de las cuatro clases: release, versión, dependencias, CI, tests o estilo. |
| `error_modelo` | La etiqueta es razonable y el mensaje o los archivos alcanzaban: es un error real del modelo. |

## Quién decidió cada causa

De los 50 errores de la muestra: **0 confirmados** por una persona, **50 revisados** por el asistente en una segunda pasada con el diff, **0 propuestos** por el asistente sin más revisión y 0 sin causa.

> **Esto no es todavía un análisis de errores hecho por una persona.** Las causas `propuesta` las puso el asistente leyendo el mensaje y los archivos de cada commit. Las `revisada` pasaron por una segunda lectura del asistente, esta vez con el diff, hecha a pedido del autor del repo y con cambios de causa donde el diff lo pedía. Ninguna la vio una persona: son un punto de partida para revisar, no un resultado. Confirmar o corregir una: editar `data/processed/errores_causas.csv` y poner `confirmada` en su estado.

## Cuántos errores hay de cada causa

Sobre la muestra (10 por repositorio), no sobre todos los errores.

| causa | errores | de la muestra | revisados | confirmados |
|---|---:|---:|---:|---:|
| `etiqueta_autor` | 21 | 42,0% | 21 | 0 |
| `mixto` | 1 | 2,0% | 1 | 0 |
| `mensaje_inutil` | 3 | 6,0% | 3 | 0 |
| `fuera_de_clases` | 7 | 14,0% | 7 | 0 |
| `error_modelo` | 18 | 36,0% | 18 | 0 |

Por repositorio:

| repositorio | `etiqueta_autor` | `mixto` | `mensaje_inutil` | `fuera_de_clases` | `error_modelo` |
|---|---:|---:|---:|---:|---:|
| angular/angular-cli | 7 | 0 | 0 | 1 | 2 |
| nuxt/nuxt | 2 | 0 | 1 | 1 | 6 |
| sveltejs/svelte | 6 | 0 | 0 | 0 | 4 |
| vitejs/vite | 2 | 0 | 1 | 2 | 5 |
| vitest-dev/vitest | 4 | 1 | 1 | 3 | 1 |

## Los errores, agrupados por causa

`verdad` es la etiqueta que puso el autor; `predicción`, lo que dijo el modelo. Mensaje y archivos recortados a una línea; el commit completo se busca con el sha.

### `etiqueta_autor` — 21

La etiqueta que puso el autor es discutible: lo que predijo el modelo se defiende.

| id | repo | verdad → predicción | mensaje | archivos | estado | nota |
|---|---|---|---|---|---|---|
| 33656f7a | angular/angular-cli | `fix` → `feat` | allow custom registry for node package task | etc/api/angular_devkit/schematics/tools/index.d.ts \| packages/angula… (4) | revisada | permite un registro propio: capacidad nueva, el autor puso fix |
| 479bfd4f | angular/angular-cli | `fix` → `feat` | initialize the DI tokens with `null` to avoid requiring them to be set to optional This c… | goldens/public-api/angular/ssr/tokens/index.api.md \| packages/angula… (2) | revisada | el diff cambia el tipo público de los tokens a `\| null` y su documentación: cambio de API, feat es defendible aunque e… |
| 58ca30b1 | angular/angular-cli | `fix` → `feat` | update `@angular-devkit/build-ng-packagr` when migrating Closes #12642 | packages/schematics/angular/migrations/migration-collection.json \| p… (4) | revisada | agrega una migración nueva (91 líneas en archivos nuevos); el autor puso fix por el issue cerrado |
| 7d540113 | angular/angular-cli | `refactor` → `fix` | update test runner to use proxess.exit instead of treekill This fixes an issue on Linux C… | tests/legacy-cli/e2e/utils/test_process.ts (1) | revisada | el propio mensaje dice "this fixes an issue"; el autor puso refactor |
| 8d8ba4f6 | angular/angular-cli | `fix` → `feat` | allow overriding Vitest coverage `reportsDirectory` option The Vitest `reportsDirectory`… | packages/angular/build/src/builders/unit-test/runners/vitest/plugins.… (2) | revisada | "can now be customized": capacidad nueva, el autor puso fix |
| 97c0cf86 | angular/angular-cli | `refactor` → `fix` | add Jest test execution to Jest builder This runs Jest on the outputs of the built test f… | packages/angular_devkit/build_angular/package.json \| packages/angula… (3) | revisada | "add Jest test execution": es feat; el autor puso refactor y el modelo tampoco acertó |
| cacb1273 | angular/angular-cli | `refactor` → `fix` | fix dependencies and import paths for strict deps requirements | packages/angular/pwa/BUILD.bazel (1) | revisada | el mensaje empieza con "fix"; el autor puso refactor |
| 0598aa0b | nuxt/nuxt | `fix` → `refactor` | do not import nitro deps in builders (#34054) | packages/nitro-server/src/index.ts \| packages/nuxt/src/core/nuxt.ts… (6) | revisada | reorganiza qué se importa en los builders; sin bug descrito, refactor es defendible |
| 3e0408bd | nuxt/nuxt | `fix` → `feat` | expose `loadBuilder` error cause | packages/nuxt/src/core/builder.ts (1) | revisada | expone la causa de un error: mejora pequeña, feat es defendible |
| 0236cf87 | sveltejs/svelte | `fix` → `feat` | better support for top-level snippet declarations (#9898) | packages/svelte/src/compiler/phases/3-transform/client/visitors/templ… (3) | revisada | "better support" agrega soporte y pruebas nuevas; feat es defendible |
| 212b6020 | sveltejs/svelte | `feat` → `fix` | support HMR with custom elements (#12926) closes https://github.com/sveltejs/svelte-hmr/i… | packages/svelte/src/compiler/phases/3-transform/client/transform-clie… (1) | revisada | el diff agrega una guarda para no redefinir el custom element en cada recarga (HMR): se lee como fix, aunque el autor p… |
| 3c84c21a | sveltejs/svelte | `fix` → `refactor` | improve controlled each block cleanup performance (#11839) | packages/svelte/src/internal/client/dom/blocks/each.js \| packages/sv… (3) | revisada | mejora de rendimiento sin bug: refactor es defendible |
| 4715dfaa | sveltejs/svelte | `feat` → `fix` | migrate `Component` to `ComponentExports<typeof Component>` in TS (#13656) Closes #13491… | packages/svelte/src/compiler/migrate/index.js \| packages/svelte/test… (3) | revisada | el diff agrega comportamiento nuevo a la migración (TSTypeReference); el issue cerrado hace defendible tanto fix como f… |
| 474c5880 | sveltejs/svelte | `fix` → `feat` | disallow `bind:group` to snippet parameters (#15401) | documentation/docs/98-reference/.generated/compile-errors.md \| packa… (6) | revisada | agrega una validación nueva con su mensaje de error y documentación: feat es defendible |
| bcf23caf | sveltejs/svelte | `fix` → `refactor` | expose `CompileError` interface, not class (#12255) * refactor CompileError stuff * chang… | packages/svelte/scripts/process-messages/templates/compile-errors.js… (6) | revisada | el propio mensaje dice "refactor CompileError stuff"; el autor puso fix por el cambio de API |
| 5a111ced | vitejs/vite | `fix` → `refactor` | replace chalk with picocolors (#6277) | packages/vite/LICENSE.md \| packages/vite/package.json \| packages/vi… (27) | revisada | cambio de librería sin bug: refactor es defendible, el autor puso fix |
| a0702a1e | vitejs/vite | `feat` → `fix` | improve error when build output missing (#12096) | packages/vite/src/node/preview.ts (1) | revisada | mejora un mensaje de error: fix es defendible |
| 183e3b7c | vitest-dev/vitest | `fix` → `feat` | cleaner compact error output (#266) | packages/vitest/src/reporters/error.ts (1) | revisada | mejora la salida de errores: feat es defendible |
| 8d4a04ea | vitest-dev/vitest | `feat` → `fix` | use `mlly` to detect externalizing | package.json \| pnpm-lock.yaml \| src/node/execute.ts (3) | revisada | cambia una dependencia interna para detectar externalización; ni feat ni fix son claros |
| 8ee59f0d | vitest-dev/vitest | `fix` → `feat` | show diff on `toContain/toMatch` assertion error (#5267) | docs/api/expect.md \| packages/expect/src/jest-expect.ts \| test/core… (4) | revisada | "show diff on ..." agrega salida nueva: feat es defendible, el autor puso fix |
| e84e2184 | vitest-dev/vitest | `fix` → `refactor` | generate a separate config for "vitest init browser" instead of a workspace file (#7934) | packages/vitest/src/create/browser/creator.ts \| test/cli/fixtures/br… (3) | revisada | cambia lo que genera un comando ("instead of a workspace file"): fix o refactor, ambos defendibles |

### `mixto` — 1

El commit hace de verdad varias cosas de peso; ninguna etiqueta única es correcta.

| id | repo | verdad → predicción | mensaje | archivos | estado | nota |
|---|---|---|---|---|---|---|
| 9dd26e26 | vitest-dev/vitest | `docs` → `fix` | update nextjs example (#1174) * fix next/image hostname error in nextjs * update react 18… | examples/nextjs/.gitignore \| examples/nextjs/next.config.js \| examp… (4) | revisada | actualiza un ejemplo, corrige un error de hostname y sube react a la vez |

### `mensaje_inutil` — 3

El mensaje no dice qué se hizo (`wip`, `update`, `changes`), así que no hay de dónde aprender.

| id | repo | verdad → predicción | mensaje | archivos | estado | nota |
|---|---|---|---|---|---|---|
| c72093b1 | nuxt/nuxt | `fix` → `feat` | separate routes for different suspense forks (#6275) | packages/nuxt/src/app/components/nuxt-root.vue \| packages/nuxt/src/a… (4) | revisada | el mensaje describe el mecanismo y no el problema; el diff muestra que arregla la ruta activa bajo suspense, pero solo… |
| 7ddbf96a | vitejs/vite | `feat` → `fix` | explicit the word boundary (#6876) | packages/playground/assets/__tests__/assets.spec.ts \| packages/playg… (3) | revisada | "explicit the word boundary" no dice qué cambia ni por qué |
| 85fce583 | vitest-dev/vitest | `feat` → `refactor` | rerun tasks | packages/ui/client/components/Navigation.vue \| packages/ui/client/co… (9) | revisada | "rerun tasks": dos palabras y 9 archivos de UI; el mensaje no alcanza |

### `fuera_de_clases` — 7

No es ninguna de las cuatro clases: release, versión, dependencias, CI, tests o estilo.

| id | repo | verdad → predicción | mensaje | archivos | estado | nota |
|---|---|---|---|---|---|---|
| 00f21d3a | angular/angular-cli | `refactor` → `fix` | removed unused lint comment (#4950) | packages/@angular/cli/blueprints/ng/files/protractor.conf.js (1) | revisada | quitar un comentario de lint sin uso: limpieza, no es ninguna de las cuatro |
| 9fe2541c | nuxt/nuxt | `fix` → `refactor` | add `pkg-types` to dependencies | packages/schema/build.config.ts \| packages/schema/package.json \| pn… (3) | revisada | agrega una dependencia que faltaba: manejo de dependencias |
| 8a13d633 | vitejs/vite | `feat` → `docs` | update rolldown to 1.1.1 (#22593) | docs/package.json \| package.json \| packages/vite/package.json \| pl… (5) | revisada | actualización de una dependencia |
| ab967c09 | vitejs/vite | `feat` → `refactor` | update esbuild to 0.18.2 (#13525) | packages/vite/package.json \| packages/vite/src/node/plugins/esbuild.… (3) | revisada | actualización de esbuild con ajustes de código |
| 2118ba97 | vitest-dev/vitest | `refactor` → `fix` | bold shortcuts help (#636) | packages/vitest/src/node/stdin.ts (1) | revisada | cambio cosmético de un texto de ayuda (+1/-1) |
| 263b7167 | vitest-dev/vitest | `feat` → `fix` | bump minimum node version to 18 and match Vite 5 requirement (#4296) | packages/vite-node/package.json \| packages/vitest/package.json \| pa… (4) | revisada | sube la versión mínima de node: versión y dependencias |
| c01c2ff0 | vitest-dev/vitest | `docs` → `fix` | set node to 20, update tsx (#4629) | netlify.toml \| package.json \| pnpm-lock.yaml (3) | revisada | configuración de netlify y versión de node: ni docs ni fix |

### `error_modelo` — 18

La etiqueta es razonable y el mensaje o los archivos alcanzaban: es un error real del modelo.

| id | repo | verdad → predicción | mensaje | archivos | estado | nota |
|---|---|---|---|---|---|---|
| 9d6c1dad | angular/angular-cli | `refactor` → `fix` | remove old worker_threads detection We now don't support Node 10 hence `worker_threads` a… | packages/angular_devkit/build_angular/src/utils/action-executor.ts (1) | revisada | quita código muerto sin cambiar comportamiento: refactor claro, el modelo lo leyó como fix |
| cabe95c5 | angular/angular-cli | `refactor` → `fix` | pre-warm transformer worker pool and pass static options via workerData Eagerly instantia… | packages/angular/build/src/tools/esbuild/javascript-transformer-worke… (2) | revisada | optimización de rendimiento sin bug; el modelo lo leyó como fix |
| 4be430e1 | nuxt/nuxt | `feat` → `docs` | pass nuxt instance to `getCachedData` (#26287) | docs/3.api/2.composables/use-async-data.md \| docs/3.api/2.composable… (3) | revisada | cambia una API en asyncData.ts (feat); el modelo se dejó llevar por 2 archivos .md de 3 |
| 864d2683 | nuxt/nuxt | `feat` → `refactor` | `addWebpackPlugin` and `addVitePlugin` utils (#368) | packages/kit/src/module/utils.ts (1) | revisada | agrega dos utilidades nuevas: feat claro, el modelo dijo refactor |
| 9a035a15 | nuxt/nuxt | `refactor` → `feat` | within nuxt app, import directly from source file (#18902) | packages/nuxt/src/app/components/island-renderer.ts \| packages/nuxt/… (29) | revisada | cambia imports en 29 archivos sin cambiar comportamiento: refactor claro, el modelo dijo feat |
| 9e5a3cdc | nuxt/nuxt | `fix` → `refactor` | avoid redirect with different encoding and trailing slash (#4857) Co-authored-by: Pooya P… | packages/nuxt/package.json \| packages/nuxt/src/app/plugins/router.ts… (7) | revisada | "avoid redirect..." describe un bug; el modelo lo leyó como refactor por los 7 archivos |
| bb4ed5e4 | nuxt/nuxt | `fix` → `feat` | add back default `baseUrl` in `tsconfig.json` (#21632) | .github/workflows/ci.yml \| package.json \| packages/nuxi/src/utils/p… (7) | revisada | restaura el valor por defecto (fix); el diff incluye también matriz de CI y pruebas de tipos, y el modelo se fue con "a… |
| dd12b243 | nuxt/nuxt | `refactor` → `fix` | replace `runInNewContext` with AST walker | packages/nuxt/src/pages/utils.ts \| packages/nuxt/test/is-serializabl… (2) | revisada | "replace X with Y" es refactor típico; el modelo dijo fix |
| 67bf7a80 | sveltejs/svelte | `fix` → `feat` | correct start of `{:else if}` and `{:else}` (#12043) The modern AST is an opportunity to… | packages/svelte/src/compiler/legacy.js \| packages/svelte/src/compile… (8) | revisada | el diff corrige dónde empieza el nodo else (fix); las 391 líneas son casi todas muestras de prueba |
| 7719d031 | sveltejs/svelte | `fix` → `refactor` | perf regression with async mode (#17461) * perf: use Set for new_deps to avoid O(n) inclu… | packages/svelte/src/compiler/phases/3-transform/client/visitors/Const… (7) | revisada | "perf regression" es un fix; el modelo dijo refactor |
| bec7ca79 | sveltejs/svelte | `fix` → `docs` | throw on invalid `{@tag}`s (#17256) * throw on invalid `{@tag}`s * fix | documentation/docs/98-reference/.generated/compile-errors.md \| packa… (4) | revisada | agrega un error de validación; el modelo dijo docs por 2 archivos .md generados |
| c7121aa3 | sveltejs/svelte | `feat` → `fix` | add type of `$effect.active` (#9624) | packages/svelte/src/main/ambient.d.ts (1) | revisada | "add type of..." es feat; el modelo dijo fix |
| 00669e13 | vitejs/vite | `feat` → `fix` | allow initializing non-empty directory (#15272) | packages/create-vite/src/index.ts (1) | revisada | "allow initializing..." es feat; el modelo dijo fix |
| 9e51a76b | vitejs/vite | `feat` → `fix` | exports `dynamicDeps` for ssrTransform, close #4898 (#4909) | packages/vite/src/node/server/transformRequest.ts \| packages/vite/sr… (3) | revisada | "exports ..." agrega una exportación: feat claro, el modelo se fue con el issue cerrado |
| b529b6fa | vitejs/vite | `docs` → `feat` | add `vitepress-plugin-group-icons` (#18132) | docs/.vitepress/config.ts \| docs/.vitepress/theme/index.ts \| docs/c… (17) | revisada | todo es documentación del sitio (docs/.vitepress); el modelo dijo feat por el plugin |
| d23a493c | vitejs/vite | `feat` → `docs` | load postcss config within workspace root only (#18440) | docs/config/shared-options.md \| packages/vite/src/node/plugins/css.ts (2) | revisada | cambia el comportamiento de la configuración de postcss (feat); el modelo dijo docs por un .md |
| fe4dc8d3 | vitejs/vite | `feat` → `fix` | customize ErrorOverlay (#10234) | packages/vite/src/client/overlay.ts (1) | revisada | "customize ErrorOverlay" es feat; el modelo se fue con la palabra "error" |
| 07ec3779 | vitest-dev/vitest | `fix` → `feat` | prevent `reportsDirectory` from removing user's project (#5376) | docs/config/index.md \| packages/vitest/src/node/config.ts \| test/co… (3) | revisada | el diff agrega una validación que lanza un error para no borrar el proyecto del usuario: fix claro; el modelo dijo feat |
