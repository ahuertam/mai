# TODO de MAI

- Añadir memoria de sesión y contexto entre tareas
- Validar planes y pedir confirmación para pasos peligrosos
- Implementar reintentos y backoff por paso
- Añadir timeouts configurables y límites de recursos
- Incorporar nuevas herramientas: `git`, `http_request`, `browser` con scraping seguro
- Mejorar operaciones de archivos: copiar/mover/eliminar con salvaguardas
- Gestionar procesos: iniciar, listar, terminar de forma segura
- Persistir logs en `logs/mai.log` y rotación de archivos
- Añadir métricas: duración por paso y tasa de éxito
- Modo `dry-run` y nivel `verbose` para depuración
- CLI para pausar/continuar/cancelar tareas y ver historial
- Integración LiveKit: control por voz y feedback en tiempo real
- Selección dinámica de modelo por tipo de tarea
- Cache de prompts/planes y control de temperatura
- Pruebas unitarias para `Executor` y simulaciones de planes