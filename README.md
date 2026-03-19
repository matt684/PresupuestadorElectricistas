# ⚡ PresupuestoElec

Calculadora de mano de obra eléctrica para instaladores argentinos.  
Precios basados en los tarifarios de [Electro Instalador](https://www.electroinstalador.com/paginas/p19-costos-de-mano-de-obra), actualizados automáticamente cada mes.

---

## ¿Qué hace?

- Calculá mano de obra por tipo de trabajo y zona del país
- Armá un presupuesto completo con tus datos y el logo de tu empresa
- Exportá a PDF o compartí por WhatsApp
- Los precios se actualizan solos el 1° de cada mes

## Estructura del proyecto

```
presupuestoelec/
├── index.html                          # La app completa (un solo archivo)
├── scripts/
│   ├── actualizar_precios.py           # Script de scraping
│   └── ultimo_scraping.json            # Log del último scraping (auto-generado)
└── .github/
    └── workflows/
        └── actualizar-precios.yml      # GitHub Action mensual
```

## Cómo publicarlo (paso a paso)

### 1. Crear el repositorio en GitHub

1. Entrá a [github.com](https://github.com) y creá una cuenta si no tenés
2. Cliqueá **New repository**
3. Nombre: `presupuestoelec` (o el que elijas)
4. Dejalo en **Public** (necesario para GitHub Pages gratis)
5. Cliqueá **Create repository**

### 2. Subir los archivos

Opción A — desde la web (más fácil):
1. En el repo recién creado, cliqueá **uploading an existing file**
2. Arrastrá todos los archivos manteniendo la estructura de carpetas
3. Cliqueá **Commit changes**

Opción B — desde la terminal:
```bash
git clone https://github.com/TU_USUARIO/presupuestoelec.git
cp -r /ruta/a/los/archivos/* presupuestoelec/
cd presupuestoelec
git add .
git commit -m "🚀 Primera versión"
git push
```

### 3. Activar GitHub Pages

1. En el repo → **Settings** → **Pages**
2. En *Source* seleccioná **Deploy from a branch**
3. Branch: `main` / Folder: `/ (root)`
4. Cliqueá **Save**
5. En 1-2 minutos la app estará en: `https://TU_USUARIO.github.io/presupuestoelec`

### 4. Verificar el GitHub Action

1. En el repo → **Actions**
2. Deberías ver el workflow **Actualizar precios mensuales**
3. Para probarlo manualmente: cliqueá en el workflow → **Run workflow**
4. El Action corre automáticamente el día 1 de cada mes

## Actualización manual de precios

Si querés actualizar los precios sin esperar al día 1:

```bash
# Instalar dependencias
pip install requests beautifulsoup4

# Correr el script
python scripts/actualizar_precios.py
```

El script modifica `index.html` directamente. Después hacé commit y push.

## Dominio propio (opcional)

Si en el futuro querés usar un dominio propio (ej: `presupuestoelec.com.ar`):

1. Comprá el dominio en NIC.ar o cualquier registrador
2. En GitHub Pages → **Custom domain** → ingresá tu dominio
3. En tu DNS agregá un registro CNAME apuntando a `TU_USUARIO.github.io`

---

## Tecnologías

- HTML + CSS + JavaScript vanilla (sin frameworks, sin dependencias)
- GitHub Actions para automatización
- GitHub Pages para hosting
- Python + BeautifulSoup para el scraping mensual

## Fuente de datos

Precios de referencia según encuestas zonales publicadas por  
**Electro Instalador** — [electroinstalador.com](https://www.electroinstalador.com)  
Para empresa unipersonal monotributista. No incluye materiales, viáticos ni cargas sociales.

---

*Hecho con ⚡ para electricistas argentinos*
