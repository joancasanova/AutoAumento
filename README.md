# AutoAumento

**AutoAumento** es una aplicación de línea de comandos (CLI) en Python que ejecuta tres grandes tareas sobre textos usando un modelo de lenguaje (LLM):
1. **Generar texto** (comando `generate`)
2. **Parsear / Analizar texto** (comando `parse`)
3. **Verificar texto** (comando `verify`)

Además, existen otros dos comandos *placeholder* llamados `pipeline` y `benchmark` que no están implementados en su totalidad.

## Tabla de Contenidos
1. [Estructura del Proyecto](#estructura-del-proyecto)
2. [Instalación](#instalación)
3. [Uso](#uso)
   - [General](#general)
   - [1) Generar Texto](#1-generar-texto)
   - [2) Parsear Texto](#2-parsear-texto)
   - [3) Verificar Texto](#3-verificar-texto)
   - [Archivos JSON de Ejemplo](#archivos-json-de-ejemplo)
4. [Pruebas](#pruebas)
5. [Contribuir](#contribuir)
6. [Licencia](#licencia)

---

## Estructura del Proyecto

La estructura es la siguiente:

```
├── app/
│   ├── application/
│   │   └── use_cases/
│   │       ├── generate_text_use_case.py
│   │       ├── parse_generated_output_use_case.py
│   │       └── verify_use_case.py
│   ├── domain/
│   │   ├── model/
│   │   │   └── entities/
│   │   │       ├── generation.py
│   │   │       ├── parsing.py
│   │   │       └── verification.py
│   │   ├── ports/
│   │   │   └── llm_port.py
│   │   └── services/
│   │       ├── parse_service.py
│   │       ├── placeholder_service.py
│   │       └── verifier_service.py
│   └── infrastructure/
│       └── external/
│           └── llm/
│               └── instruct_model.py
├── app/main.py
├── pyproject.toml
└── README.md
```

- **app/**: Contiene la lógica principal dividida en tres capas:
  - **application/use_cases**: Casos de uso concretos (generate, parse, verify).
  - **domain/**: Modelos de datos (entities), puertos (interfaces) y servicios.
  - **infrastructure/**: Integraciones externas (p.ej. con Hugging Face).
- **app/main.py**: Punto de entrada para la línea de comandos.
- **pyproject.toml**: Administrador de dependencias y configuración general del proyecto.
- **README.md**: Este archivo (documentación).

---

## Instalación

1. **Clonar el repositorio**:
   ```bash
   git clone https://github.com/tu-usuario/autoaumento.git
   cd autoaumento
   ```

2. **Crear y activar un entorno virtual** (recomendable):
   ```bash
   python -m venv .venv
   # Linux/Mac:
   source .venv/bin/activate
   # Windows:
   .venv\Scripts\activate
   ```

3. **Instalar dependencias** usando `pyproject.toml`:
   ```bash
   pip install --upgrade pip
   pip install -e ".[dev]"
   ```
   Esto instalará las librerías principales (transformers, typer, etc.) y las de desarrollo (pytest, black, pylint...).

---

## Uso

Una vez instalado, puedes ejecutar la herramienta desde la raíz del proyecto con:
```bash
python app/main.py <comando> [opciones]
```

### General

Existen *subcomandos* principales:
- `generate`: Genera texto llamando a un LLM de Hugging Face.
- `parse`: Analiza un texto según reglas definidas.
- `verify`: Verifica la corrección de salidas basándose en métodos de verificación.
- `pipeline` y `benchmark`: Placeholder (no implementado).

Para ver la ayuda de un subcomando (ej. `generate`):
```bash
python app/main.py generate --help
```

---

### 1) Generar Texto

**Objetivo**: Llamar a un modelo de lenguaje (LLM) y obtener uno o varios textos generados.

**Uso básico**:
```bash
python app/main.py generate \
  --gen-model-name "Qwen/Qwen2.5-1.5B-Instruct" \
  --system-prompt "Eres un asistente útil." \
  --user-prompt "Explica la computación cuántica de forma sencilla." \
  --num-sequences 2 \
  --max-tokens 50 \
  --temperature 0.9 \
  --reference-data "reference.json"
```

**Parámetros principales**:
- `--gen-model-name`: Nombre (ruta) del modelo a usar (por defecto "Qwen/Qwen2.5-1.5B-Instruct").
- `--system-prompt`: Prompt “sistema” que da contexto general al LLM.
- `--user-prompt`: Prompt del usuario (pregunta principal).
- `--num-sequences`: Cuántas respuestas generar (p.ej. 2).
- `--max-tokens`: Máximo de *tokens* generados por secuencia.
- `--temperature`: Controla aleatoriedad (1.0 = normal, >1 = más creativo).
- `--reference-data`: (Opcional) un archivo `.json` con datos para *placeholders*.

**Placeholders**:
- Si tus prompts contienen texto del tipo `"{nombre}"`, el programa los sustituirá si pasas un JSON de referencia.  
- Ejemplo:  
  - **Prompts**:
    ```
    system_prompt = "Eres un asistente experto en {tema}."
    user_prompt = "¿Puedes explicar algo relacionado con {tema} y {subtema}?"
    ```
  - **reference.json**:
    ```json
    {
      "tema": "astrofísica",
      "subtema": "agujeros negros"
    }
    ```
  - Al ejecutar `generate`, esos placeholders serán remplazados.  
  - **Resultado**: `Eres un asistente experto en astrofísica.` etc.

---

### 2) Parsear Texto

**Objetivo**: Analizar texto en busca de patrones (regex o “palabras clave”) y extraer información estructurada.

**Uso básico**:
```bash
python app/main.py parse \
  --text "Usuario: Ana, Edad: 30. Usuario: Luis, Edad: 25." \
  --rules "rules.json" \
  --output-filter "all"
```
- `--text`: Cadena a analizar.
- `--rules`: Archivo JSON que describe las reglas de parseo.
- `--output-filter`: Cómo filtrar los resultados finales. Valores posibles:
  - `all` (devuelve todos los parseos),
  - `successful` (solo parseos completos, sin faltar campos),
  - `first`,
  - `first_n` (usa `--output-limit` para indicar cuántos).

El comando devuelve en pantalla un **JSON** con las ocurrencias encontradas, según las reglas.

#### Estructura de `rules.json`
Cada regla puede ser **regex** o **keyword**:

```json
[
  {
    "name": "Usuario",
    "mode": "keyword",
    "pattern": "Usuario:",
    "secondary_pattern": ", Edad:"
  },
  {
    "name": "Edad",
    "mode": "regex",
    "pattern": "Edad:\\s*(\\d+)"
    "fallback_value": "missing_edad"
  }
]
```
- `name`: Identificador único de la regla (ej. "Usuario").
- `mode`: `"regex"` o `"keyword"`.
- `pattern`: El patrón principal (si mode=regex, es una expresión regular; si mode=keyword, es la palabra clave que buscamos).
- `secondary_pattern` (opcional): Si `mode` es `keyword`, define un *límite* hasta donde se extrae el texto.
- `fallback_value` (opcional): Valor por defecto si no se encuentra coincidencia.

Ejemplo de parseo:
```
Texto: "Usuario: Ana, Edad: 30. Usuario: Luis, Edad: 25."

Reglas (simplificadas):
- Usuario (keyword): "Usuario:", y secondary_pattern=", Edad:"
- Edad (regex): "Edad:\s*(\d+)"

Salida JSON:
[
  {
    "Usuario": "Ana",
    "Edad": "30"
  },
  {
    "Usuario": "Luis",
    "Edad": "25"
  }
]
```

---

### 3) Verificar Texto

**Objetivo**: Realizar verificaciones sobre textos usando métodos LLM. Por ejemplo, comprobar si un LLM genera respuestas que contengan ciertas palabras clave o que cumplan algún criterio.

**Uso básico**:
```bash
python app/main.py verify \
  --verify-model-name "Qwen/Qwen2.5-3B-Instruct" \
  --methods "methods.json" \
  --required-confirmed 2 \
  --required-review 1 \
  --reference-data "verify_data.json"
```
- `--verify-model-name`: Modelo a usar en la verificación (similar a `generate`).
- `--methods`: Archivo JSON con la definición de métodos de verificación (ver más abajo).
- `--required-confirmed`: Número mínimo de “verificaciones positivas” para dar la verificación como *confirmada*.
- `--required-review`: Número mínimo de “verificaciones positivas” para marcar como *revisión*.  
  Si no se llega a este número, se descarta.  
- `--reference-data`: (Opcional) Igual que en generate: placeholders sustituidos en prompts de verificación.

#### Estructura de `methods.json`
Ejemplo de `methods.json`:
```json
[
  {
    "mode": "cumulative",
    "name": "CheckPalabraClave",
    "system_prompt": "Eres un verificador que busca la palabra 'holaaa'.",
    "user_prompt": "holaaa, como estáaaas??.",
    "valid_responses": ["holaaa"],
    "num_sequences": 3,
    "required_matches": 2
  },
  {
    "mode": "eliminatory",
    "name": "CheckRespuestaFormal",
    "system_prompt": "Eres un verificador estricto. Asegúrate que no se use lenguaje informal. ¿Tiene la siguiente frase un tono formal?",
    "user_prompt": "Qué pasa, nos hacemos algo chulo o qué",
    "valid_responses": ["Sí", "Si", "Yes"],
    "num_sequences": 2,
    "required_matches": 2
  }
]
```
**Campos principales**:
- `mode`: `"eliminatory"` o `"cumulative"`.
  - **eliminatory**: Si falla *una* de estas verificaciones, se descarta todo.
  - **cumulative**: Suma a la cuenta de métodos pasados si funciona.
- `name`: Nombre identificador de la verificación.
- `system_prompt`: Prompt sistema que explica al LLM cómo verificar.
- `user_prompt`: Prompt usuario o la pregunta concreta de verificación.
- `valid_responses`: Lista de posibles frases que se consideran “respuesta válida”.
- `num_sequences`: Cuántas secuencias genera el verificador para checar coincidencias.
- `required_matches`: Cuántas secuencias deben cumplir la condición para pasar la verificación.

Al final se imprime un JSON con el resumen de verificación:
```json
{
  "final_status": "discarded",
  "success_rate": 0.5,
  "execution_time": 1.2345,
  "results": [
    {
      "method_name": "CheckPalabraClave",
      "mode": "cumulative",
      "passed": true,
      "score": 1.0,
      "timestamp": "2024-01-01T12:00:00",
      "details": {
        "total_responses": 3,
        "positive_responses": 3,
        "valid_responses": ["holaaa"],
        "required_matches": 2
      }
    },
    {
      "method_name": "CheckRespuestaFormal",
      "mode": "eliminatory",
      "passed": false,
      "score": 0.0,
      "timestamp": "2024-01-01T12:00:01",
      "details": {
        "total_responses": 2,
        "positive_responses": 0,
        "valid_responses": ["Sí", "Si", "Yes"],
        "required_matches": 2
      }
    }
  ]
}
```
En este ejemplo, se obtuvo `final_status: "discarded"` porque la primera verificación *cumulative* pasó, pero la segunda *eliminatory* falló (eso lleva directamente a *discarded*).

---

### Archivos JSON de Ejemplo

**1) `reference.json`** (para placeholders en prompts):
```json
{
  "tema": "astrofísica",
  "subtema": "agujeros negros"
}
```

**2) `rules.json`** (para `parse`):
```json
[
  {
    "name": "Usuario",
    "mode": "keyword",
    "pattern": "Usuario:",
    "secondary_pattern": ", Edad:"
  },
  {
    "name": "Edad",
    "mode": "regex",
    "pattern": "Edad:\\s*(\\d+)",
    "fallback_value": "desconocida"
  }
]
```

**3) `methods.json`** (para `verify`):
```json
[
  {
    "mode": "cumulative",
    "name": "CheckPalabraClave",
    "system_prompt": "Eres un verificador que busca cierta palabra. ¿El texto contiene la palabra 'ejemplo'? Por favor, respóndelo claramente.",
    "user_prompt": "Un ejemplo de adicción es el abuso del tabaco",
    "valid_responses": ["ejemplo"],
    "num_sequences": 3,
    "required_matches": 2
  },
  {
    "mode": "eliminatory",
    "name": "CheckFormalidad",
    "system_prompt": "Eres un verificador formal. Asegúrate que la respuesta sea formal",
    "user_prompt": "Estimado alcalde, le escribo debido a los recientes acontecimientos...",
    "valid_responses": ["Estimado", "Saludos cordiales"],
    "num_sequences": 2,
    "required_matches": 2
  }
]
```

---

## Licencia

Distribuido bajo la **MIT License**. Consulta el archivo `LICENSE` para más detalles.

---

> **¡Listo!** Esperamos que con estas instrucciones detalladas puedas utilizar **AutoAumento** sin complicaciones. Ante cualquier duda adicional, no dudes en abrir un *issue* en el repositorio o proponer mejoras.
