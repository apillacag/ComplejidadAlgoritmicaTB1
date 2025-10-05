# Descarga y procesamiento de la red vial real de San Juan de Lurigancho (OSM)
# Librerías permitidas
import osmnx as ox  # Solo para descargar datos de OpenStreetMap
import pandas as pd  # Para guardar CSVs
from graphviz import Graph  # Para visualizaciones sencillas
from collections import deque  # Para la implementación de BFS (cola)
import random

# Configuración
ox.settings.use_cache = True
ox.settings.log_console = True

print("Descargando red vial de San Juan de Lurigancho desde OpenStreetMap...")

# 1. Descarga de la red OSM
# Aquí se usa osmnx para obtener la red 'drive' (calles transitables por vehículos)
lugar = "San Juan de Lurigancho, Lima, Peru"

try:
    # osmnx devuelve internamente un grafo compatible con networkx
    # NO importamos ni usamos networkx en este script; solo aprovechamos la descarga
    grafo_osm = ox.graph_from_place(lugar, network_type='drive', simplify=True)
    print("Red vial descargada correctamente desde OSM.")
    print(f"   (Objeto obtenido: grafo_osm con nodos y aristas de OSM)\n")
except Exception as e:
    print("Error descargando OSM:", e)
    print("Verifica conexión o intenta usar coordenadas en lugar del nombre del lugar.")
    raise SystemExit(1)

# 2. Construcción del grafo
#    - Lista de adyacencia con pesos
#    - Diccionario: { nodo: [(vecino, distancia_metros, tiempo_minutos), ...], ... }

# Parámetros de conversión distancia -> tiempo
velocidad_kmh = 30.0  # velocidad promedio urbana


def metros_a_minutos(dist_m):
    """Convierte distancia en metros a tiempo en minutos"""
    distancia_km = dist_m / 1000.0
    minutos = (distancia_km / velocidad_kmh) * 60.0
    return round(minutos, 2)


# Construimos:
# - nodos_info: diccionario con coordenadas { nodo_id: (longitud, latitud) }
# - lista_ady: diccionario de adyacencia { nodo: [(vecino, length, tiempo), ...], ... }
nodos_info = {}
lista_ady = {}

print("Construyendo lista de adyacencia...")

# Paso 1: Extraer nodos
# Recorremos todos los nodos del grafo OSM
for nodo, data in grafo_osm.nodes(data=True):
    # Guardamos coordenadas en formato (longitud, latitud)
    x = data.get('x', 0.0)
    y = data.get('y', 0.0)
    nodos_info[nodo] = (x, y)
    # Inicializamos la lista de vecinos vacía para cada nodo
    lista_ady[nodo] = []

# Paso 2: Extraer aristas
# Recorremos todas las aristas del grafo OSM
# osmnx devuelve aristas con formato (u, v, key, data)
for u, v, key, data in grafo_osm.edges(data=True, keys=True):
    # Obtenemos la longitud de la arista (distancia en metros)
    length = data.get('length', None)
    if length is None:
        # Si falta longitud, asignamos valor por defecto (100 m)
        length = 100.0

    # Convertimos distancia a tiempo
    tiempo = metros_a_minutos(length)

    # Añadimos la arista a la lista de adyacencia
    # Formato: lista_ady[u] = [(vecino, distancia, tiempo), ...]
    lista_ady[u].append((v, float(length), tiempo))

    # Verificamos si la calle es de doble sentido
    oneway = data.get('oneway', None)
    # Si no es de un solo sentido, añadimos también la arista opuesta
    if oneway in (False, 'false', 'False', 0, None):
        lista_ady[v].append((u, float(length), tiempo))

print("Lista de adyacencia construida.")
print(f"Nodos registrados: {len(nodos_info)}")

# Contar aristas
num_aristas = 0
for nodo in lista_ady:
    num_aristas = num_aristas + len(lista_ady[nodo])
num_aristas = num_aristas // 2  # Dividimos entre 2 porque contamos cada arista dos veces

print(f"Aristas aproximadas: {num_aristas}\n")


# 3. Conectividad: obtener componente gigante (BFS)
#    - Implementación BFS (cola)

def BFS_componente(grafo_adj, inicio):
    """
    BFS que devuelve el conjunto de nodos alcanzables desde 'inicio'
    grafo_adj: diccionario de adyacencia { nodo: [(vecino, dist, tiempo), ...], ... }
    """
    visitados = set()
    colaAuxiliar = deque([inicio])
    visitados.add(inicio)

    while colaAuxiliar:
        nodo = colaAuxiliar.popleft()
        # Recorremos todos los vecinos del nodo actual
        for vecino_info in grafo_adj.get(nodo, []):
            vecino = vecino_info[0]  # El vecino es el primer elemento de la tupla
            if vecino not in visitados:
                colaAuxiliar.append(vecino)
                visitados.add(vecino)

    return visitados


# Revisar conectividad general iterando componentes
print("Verificar componentes conexas con BFS...")

todos_nodos = set()
# Agregar todos los nodos a un conjunto
for nodo in lista_ady.keys():
    todos_nodos.add(nodo)

componentes = []
visitados_global = set()

# Recorremos todos los nodos para encontrar componentes
for nodo in todos_nodos:
    if nodo not in visitados_global:
        # Encontramos una nueva componente
        comp = BFS_componente(lista_ady, nodo)
        componentes.append(comp)
        # Agregamos todos los nodos de esta componente a visitados_global
        for n in comp:
            visitados_global.add(n)

# Ordenar componentes por tamaño (de mayor a menor)
# Usamos una lista auxiliar con tuplas (tamaño, componente)
componentes_con_tamanio = []
for comp in componentes:
    componentes_con_tamanio.append((len(comp), comp))

# Ordenamos por tamaño (primer elemento de la tupla)
componentes_con_tamanio.sort(reverse=True)

# Extraemos solo las componentes ordenadas
componentes = []
for tamanio, comp in componentes_con_tamanio:
    componentes.append(comp)

# La componente principal es la más grande
if len(componentes) > 0:
    componente_principal = componentes[0]
else:
    componente_principal = set()

if len(componentes) <= 1:
    print("El grafo está completamente conectado (1 componente).")
else:
    print(f"Grafo con {len(componentes)} componentes. Usaremos el componente principal (el mayor).")
    print(f"Tamaño componente principal: {len(componente_principal)} nodos")

    # Reducir lista de adyacencia al componente principal
    # Paso 1: Crear nueva lista de adyacencia solo con nodos del componente principal
    nueva_lista_ady = {}
    for nodo in componente_principal:
        nueva_lista_ady[nodo] = []
        # Recorremos los vecinos del nodo
        for vecino_info in lista_ady[nodo]:
            vecino = vecino_info[0]
            length = vecino_info[1]
            tiempo = vecino_info[2]
            # Solo agregamos el vecino si también está en el componente principal
            if vecino in componente_principal:
                nueva_lista_ady[nodo].append((vecino, length, tiempo))

    # Reemplazamos la lista de adyacencia
    lista_ady = nueva_lista_ady

    # Paso 2: Actualizar nodos_info solo con nodos del componente principal
    nueva_nodos_info = {}
    for nodo in componente_principal:
        nueva_nodos_info[nodo] = nodos_info[nodo]

    nodos_info = nueva_nodos_info

# 4. Guardar CSVs de aristas y nodos 
print("\nGuardando archivos CSV (aristas y nodos)...")

# Aristas: para evitar duplicados en grafo no dirigido, almacenamos pares u<v
aristas_reg = []
visto = set()

for u in lista_ady:
    lista_vec = lista_ady[u]
    # Recorremos todos los vecinos de u
    for vecino_info in lista_vec:
        v = vecino_info[0]
        length = vecino_info[1]
        tiempo = vecino_info[2]

        # Usar par ordenado para evitar duplicados (u,v) y (v,u)
        if u <= v:
            par = (u, v)
        else:
            par = (v, u)

        # Si ya procesamos este par, lo saltamos
        if par in visto:
            continue
        visto.add(par)

        # Intentamos obtener nombre de la calle desde grafo_osm
        nombre = None
        try:
            edge_data = grafo_osm.get_edge_data(u, v)
            if edge_data:
                # edge_data puede ser dict de keys -> dicts
                if isinstance(edge_data, dict):
                    # Tomamos el primer key disponible
                    primera_key = list(edge_data.keys())[0]
                    first = edge_data[primera_key]
                    nombre = first.get('name', None)
        except Exception:
            nombre = None

        # Si no tiene nombre, ponemos "Sin nombre"
        if nombre is None:
            nombre = 'Sin nombre'

        # Agregamos la arista a nuestra lista
        aristas_reg.append({
            'origen': par[0],
            'destino': par[1],
            'distancia_metros': length,
            'tiempo_minutos': tiempo,
            'nombre_calle': nombre
        })

# Guardar CSV de aristas
df_aristas = pd.DataFrame(aristas_reg)
df_aristas.to_csv('grafo_sjl_osm.csv', index=False, encoding='utf-8')
print(f"grafo_sjl_osm.csv guardado: {len(df_aristas)} aristas")

# Nodos: id, latitud (y), longitud (x)
nodos_reg = []
for nodo in nodos_info:
    coordenadas = nodos_info[nodo]
    x = coordenadas[0]  # longitud
    y = coordenadas[1]  # latitud

    nodos_reg.append({
        'nodo_id': nodo,
        'latitud': y,
        'longitud': x
    })

# Guardar CSV de nodos
df_nodos = pd.DataFrame(nodos_reg)
df_nodos.to_csv('nodos_sjl_osm.csv', index=False, encoding='utf-8')
print(f"nodos_sjl_osm.csv guardado: {len(df_nodos)} nodos")

# 5. Visualizaciones
print("\nGenerando visualizaciones...")

# 5.1 Mapa completo de SJL con osmnx
print("Generando mapa completo de SJL...")
try:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(15, 15), facecolor='white')
    ox.plot_graph(grafo_osm, ax=ax, node_size=5, node_color='blue', node_alpha=0.4,
                  edge_color='gray', edge_linewidth=0.5, bgcolor='white', show=False, close=False)
    plt.title('Red Vial Completa de San Juan de Lurigancho (OpenStreetMap)', fontsize=16, fontweight='bold', pad=20)
    plt.tight_layout()
    plt.savefig('red_completa_sjl.png', dpi=300, bbox_inches='tight')
    plt.close(fig)
    print("red_completa_sjl.png generada (mapa completo).")
except Exception as e:
    print("No se pudo generar el mapa completo con osmnx.plot_graph:", e)

# 5.2 Subgrafo de 100 nodos con graphviz
print("Seleccionando subgrafo de 100 nodos mediante BFS...")

# Si el grafo tiene menos de 100 nodos, usamos todos
if len(lista_ady) <= 100:
    subgrafo_nodos = []
    for nodo in lista_ady.keys():
        subgrafo_nodos.append(nodo)
else:
    # Seleccionamos 100 nodos usando BFS desde un nodo aleatorio
    # Convertimos las keys a lista para poder elegir un nodo aleatorio
    lista_nodos = []
    for nodo in lista_ady.keys():
        lista_nodos.append(nodo)

    nodo_inicio = random.choice(lista_nodos)
    subgrafo_nodos = []
    colaAuxiliar = deque([nodo_inicio])
    visitados_local = set([nodo_inicio])

    # BFS para obtener 100 nodos
    while len(colaAuxiliar) > 0 and len(subgrafo_nodos) < 100:
        nodo = colaAuxiliar.popleft()
        subgrafo_nodos.append(nodo)

        # Obtener vecinos del nodo actual
        vecinos = []
        for vecino_info in lista_ady.get(nodo, []):
            vecino = vecino_info[0]
            vecinos.append(vecino)

        # Mezclar vecinos aleatoriamente
        random.shuffle(vecinos)

        # Agregar vecinos no visitados a la cola
        for vec in vecinos:
            if vec not in visitados_local and len(subgrafo_nodos) + len(colaAuxiliar) < 1000:
                visitados_local.add(vec)
                colaAuxiliar.append(vec)

    # Si aún faltan nodos, completar aleatoriamente
    if len(subgrafo_nodos) < 100:
        faltan = 100 - len(subgrafo_nodos)
        extras = []
        for n in lista_ady.keys():
            if n not in subgrafo_nodos:
                extras.append(n)

        random.shuffle(extras)
        # Agregar los nodos faltantes
        for i in range(min(faltan, len(extras))):
            subgrafo_nodos.append(extras[i])

# Construir subgrafo de adyacencia (solo nodos seleccionados)
# Convertimos la lista a set para búsquedas más rápidas
conjunto_subgrafo = set(subgrafo_nodos)

subgrafo_ady = {}
for n in subgrafo_nodos:
    subgrafo_ady[n] = []
    # Recorremos los vecinos de n
    for vecino_info in lista_ady.get(n, []):
        v = vecino_info[0]
        l = vecino_info[1]
        t = vecino_info[2]
        # Solo agregamos el vecino si está en el subgrafo
        if v in conjunto_subgrafo:
            subgrafo_ady[n].append((v, l, t))

# Crear visualización con graphviz 
print("Crear visualización con graphviz...")
g = Graph('Subgrafo_100_SJL', format='png')

# Configurar tamaño y orientación del documento
g.attr(size='8,10')  # Ancho de 8 pulgadas, alto de 10 pulgadas
g.attr(dpi='300')  # Resolución moderada
g.attr(ratio='compress')  # Comprimir para ajustar mejor

# Agregar nodos al grafo con etiquetas visibles
for nodo in subgrafo_ady.keys():
    g.node(str(nodo), label=str(nodo))

# Agregar aristas sin duplicar (u<v)
agregado = set()
for u in subgrafo_ady:
    vecinos = subgrafo_ady[u]
    # Recorremos todos los vecinos de u
    for vecino_info in vecinos:
        v = vecino_info[0]
        length = vecino_info[1]
        tiempo = vecino_info[2]

        # Crear par ordenado para evitar duplicados
        if str(u) <= str(v):
            par = (u, v)
        else:
            par = (v, u)

        # Si ya agregamos esta arista, la saltamos
        if par in agregado:
            continue
        agregado.add(par)

        # Etiqueta con distancia en metros
        etiqueta = f"{int(length)} m"
        g.edge(str(par[0]), str(par[1]), label=etiqueta)

# Renderizar imagen del subgrafo
try:
    g.render('subgrafo_100_sjl_osm', format='png', cleanup=True)
    print("subgrafo_100_sjl_osm.png generada (subgrafo 100 nodos, graphviz).")
except Exception as e:
    print("No se pudo generar subgrafo con graphviz:", e)

# 6. Estadísticas del grafo
print("\nESTADÍSTICAS DEL GRAFO REAL DE SJL:")

total_nodos = len(nodos_info)

# Para contar aristas en grafo no dirigido sumamos grados y dividimos por 2
suma_grados = 0
for nodo in lista_ady:
    vecs = lista_ady[nodo]
    suma_grados = suma_grados + len(vecs)

total_aristas = suma_grados / 2.0

# Distancia total en km
dist_total_metros = 0
for u in lista_ady:
    lista = lista_ady[u]
    for vecino_info in lista:
        length = vecino_info[1]
        dist_total_metros = dist_total_metros + length

# Dividimos entre 2 porque contamos cada arista dos veces
dist_total_km = (dist_total_metros / 2.0) / 1000.0

# Grado promedio
if total_nodos > 0:
    grado_promedio = suma_grados / total_nodos
else:
    grado_promedio = 0.0

print(f"Total de intersecciones (nodos): {total_nodos}")
print(f" Total de calles (aristas, aprox): {int(total_aristas)}")

if len(componentes) == 1:
    print(f"   • Conectividad: Conectado (componente principal usado)")
else:
    print(f"Conectividad: No completamente conectado — se usó componente principal")

print(f"Distancia total de calles: {dist_total_km:.2f} km")
print(f"Grado promedio (calles por intersección): {grado_promedio:.2f}")

print("\nProceso completado. Archivos generados:")
print("grafo_sjl_osm.csv")
print("nodos_sjl_osm.csv")
print("red_completa_sjl.png")
print("subgrafo_100_sjl_osm.png\n")
