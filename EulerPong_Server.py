# -*- coding: utf-8 -*-

import pygame
from pygame.locals import *
#te importa constantes de pygame que reconocen teclas del teclado
import os
import sys #para que salga del juego si se cierra la ventana
from paho.mqtt.client import Client
import time
from multiprocessing import Process
from multiprocessing import Lock
from multiprocessing import Manager
#-----------------------------------------------------------------------------

class Message():
    
    """
    on_message está definido como una clase por la facilidad que supone
    su implementacion para transferir monitores y semaforos que entrarian en 
    juego al recibir un mensaje, y así poder pasarlos a más de un proceso.
    """
    
    def __init__(self, barra_Y_J1J2, semaforo, semaforo_clientes, dicc_conectados, lista_procesos, direccion):
        self.barra_Y_J1J2 = barra_Y_J1J2
        self.semaforo = semaforo
        self.semaforo_clientes = semaforo_clientes
        self.dicc_conectados = dicc_conectados
        self.lista_procesos = lista_procesos
        self.direccion = direccion
    #definimos los parametros en la inicializacion de la clase, que haremos
    #en el main, y los pasamos a on.message
    def on_message(self, client, userdata, msg):
        mensaje = str(msg.payload.decode("utf-8"))
        barra_Y_J1J2 = self.barra_Y_J1J2
        semaforo = self.semaforo
        semaforo_clientes = self.semaforo_clientes
        dicc_conectados = self.dicc_conectados
        lista_procesos = self.lista_procesos
        direccion = self.direccion
        topic = msg.topic
        password = topic[18:] #me ayudará a crear un topic nuevo para solo
        #esos dos jugadores
        userdata_short = mensaje[0:-20]
        #userdata para el usuario, que lo imprimirá en su juego
        userdata_long = mensaje[0:-10]
        #userdata para el servidor, que le servirá de información para saber
        #el tipo de cliente que accede.
        
        """
        Aquí se detallan todos los posibles mensajes que se pueden recibir:
        """
        
        if mensaje[-19:] == "Cliente_1.conectado":
            lista_topics = [] #agrupamos los topics para ver si el que está
            #buscando el cliente se encuentra activo en el diccionario
            semaforo_clientes.acquire()
            for key in dicc_conectados:
                lista_topics.append(key)
            if topic in lista_topics: #es que cliente2 ya está conectado
                
                userdata_1 = userdata_short
                userdata_2 = dicc_conectados[topic][1][1]
                dicc_conectados.pop(topic)
                dicc_conectados.setdefault(topic,[(1,1),(userdata_1,userdata_2)])
                #ahora los clientes ya estan conectados y listos para empezar               
                client.publish('clients/EulerPong/'+password,'SERVIDOR_CONECTADO.'+userdata_1+"&"+userdata_2)
                print("HE PUBLICADO"+'clients/EulerPong/'+password,'SERVIDOR_CONECTADO.'+userdata_1+"&"+userdata_2)
                lista_procesos.append(Process(target=juego_server, args=(barra_Y_J1J2,password,direccion)))
                lista_procesos[-1].start()
                #hemos agrupado todos los procesos en una lista para tenerlos
                #controlados
            else:#no se ha encontrado el topic, luego esa contraseña es incorrecta
                client.publish('clients/EulerPong/'+password,'NOBODY')
            semaforo_clientes.release()
            print(userdata_long,"conectado")
            
        if mensaje[-19:] == "Cliente_2.conectado": #nadie conectado antes, porque si no le echaría
            semaforo_clientes.acquire()
            dicc_conectados.setdefault(topic,[(0,1),("",mensaje[0:-20])])
            semaforo_clientes.release()          
            print(userdata_long,"conectado")
            
        if mensaje[0:3] == "J2B": #que ocurre cuando mueve la barra Jugador_2
            barra_J2 = int(mensaje[3:])
            semaforo.acquire()
            barra_J1 = barra_Y_J1J2[0][0] 
            barra_Y_J1J2.append((barra_J1,barra_J2))
            barra_Y_J1J2.pop(0)
            #barra_Y_J1J2 es un manager, así que para actualizarlo añadimos 
            #la nueva tupla de coordenadas a la lista y borramos la anterior
            semaforo.release()
            
        if mensaje[0:3] == "J1B": #análogo para Jugador_1
            barra_J1 = int(mensaje[3:])
            semaforo.acquire()
            barra_J2 = barra_Y_J1J2[0][1]
            barra_Y_J1J2.append((barra_J1,barra_J2))
            barra_Y_J1J2.pop(0)
            semaforo.release()
            
def on_connect(server, userdata, flags, rc):
    print("Servidor conectado al Broker!")
    time.sleep(1)
def on_subscribe(server, userdata, mid, granted_qos):
    print("Servidor conectado al Channel!")
    time.sleep(0.5)
    print("Esperando confirmacion de Clientes...")
    time.sleep(1)

#-----------------------------------------------------------------------------
def on_message_juego(client,userdata,msg):
    mensaje = str(msg.payload.decode("utf-8"))
    
    if mensaje == "CLIENTE_DESCONECTADO":
        print("Un cliente se ha desconectado.")
        pygame.quit()   

#-----------------------------------------------------------------------------


def carga_imagen(nombre, img_dir, alpha=False):
    """
    Función que carga la imagen solo con que pongas nombre y directorio.
    El canal Alpha sirve para crear transparencias 
    (que la bola se vea redonda)
    """
    ruta = os.path.join(img_dir, nombre)
    try:
        imagen = pygame.image.load(ruta)
    except:
        print("ERROR: No se puede cargar la imagen")
        sys.exit(1)
    if alpha == True: #La imagen es un png con transparencia
        imagen = imagen.convert_alpha()
    else: 
        imagen = imagen.convert()
    return imagen

class Pelota(pygame.sprite.Sprite):
    """
    Un sprite es un objeto de pygame que representa algo que está en la 
    pantalla y se puede mover. 
    Es recomendable crear una clase con cada sprite que tengamos en el juego, 
    es decir, con la pelota y las barras.
    """
    def __init__(self,IMG_DIR,Anchura_Pantalla,Altura_Pantalla): 
        #definimos con init las características de esta clase
        
        pygame.sprite.Sprite.__init__(self)
        self.image = carga_imagen("bola.png", IMG_DIR, alpha=True)
        #Le atribuimos la imagen al sprite
        self.rect = self.image.get_rect()
        #Le atribuimos posicion y velocidad al sprite
        self.rect.centerx = Anchura_Pantalla / 2
        self.rect.centery = Altura_Pantalla / 2
        self.speed = [7, 7]
        
    def update(self, server2, Anchura_Pantalla, Altura_Pantalla, puntosJugador_1, puntosJugador_2, password):
        
        """
        Esta función se encarga de hacer avanzar la pelota y que rebote cuando
        llegue al límite de la pantalla.
        """ 
        
        if self.rect.left < 0 or self.rect.right > Anchura_Pantalla:
            self.speed[0] = -self.speed[0]
        if self.rect.top <0 or self.rect.bottom > Altura_Pantalla:
            self.speed[1] = -self.speed[1]
        self.rect.move_ip((self.speed[0],self.speed[1]))
        bola_coord = (self.rect.centerx,self.rect.centery)
        server2.publish('clients/EulerPong/'+password,"bc."+str(bola_coord))
        #Esto avanzará o retrocederá la pelota "x" pixeles o la subirá o
        #bajará "y" pixeles
        if self.rect.left < 0:
            puntosJugador_2 = puntosJugador_2 + 1
            server2.publish('clients/EulerPong/'+password,"J2."+str(puntosJugador_2))
            self.rect.centerx = Anchura_Pantalla / 2
            self.rect.centery = Altura_Pantalla / 2
            bola_coord = (self.rect.centerx,self.rect.centery)
            
        if self.rect.right > Anchura_Pantalla:
            puntosJugador_1 = puntosJugador_1 + 1
            server2.publish('clients/EulerPong/'+password,"J1."+str(puntosJugador_1))
            self.rect.centerx = Anchura_Pantalla / 2
            self.rect.centery = Altura_Pantalla / 2   
            bola_coord = (self.rect.centerx,self.rect.centery)          
        return (puntosJugador_1, puntosJugador_2)    
        
    def colision(self, objetivo): 
        #Esto analiza que ocurre cuando un sprite choca con otro
        if self.rect.colliderect(objetivo.rect):
            self.speed[0] = -self.speed[0]
            #Al chocar con lo que sea cambiará la velocidad hacia la otra
            #dirección, en este caso lo aplicaremos cuando definamos barra

def muestra_texto(texto): #Para mostrar las puntuaciones del jugador
    font = pygame.font.Font(None, 40) #Defino tipo y tamaño de la fuente
    cadena_texto = font.render(texto,1, (1,1,1))
    #Crea una imagen del texto importado
    return cadena_texto

class Barra(pygame.sprite.Sprite): #definimos la clase de las barras
    
    def __init__(self, x, IMG_DIR, Anchura_Pantalla, Altura_Pantalla):
        #La funcion principal depende de x porque vamos a diferenciar 
        #la barra de la izquierda de la de la derecha
        self.image = carga_imagen("barra.png", IMG_DIR, alpha=True)
        self.rect = self.image.get_rect()
        self.rect.centerx = x 
        self.rect.centery = Altura_Pantalla / 2
    
#-----------------------------------------------------------------------------


def juego_server(barra_Y_J1J2,password,direccion):
    puntosJugador_1 = 0 
    puntosJugador_2 = 0
    
    Anchura_Pantalla = 800
    Altura_Pantalla = 450

    IMG_DIR = "IMAGENES"
    #es la carpeta donde van a estar las imágenes
    
    #------------------------------------------------------------------------
    time.sleep(9)
    pygame.init()
    pygame.mixer.init()
    pygame.font.init()
    #Ejecutamos pygame
    pantalla = pygame.display.set_mode((Anchura_Pantalla, Altura_Pantalla))
    #Creamos pantalla con las dimensiones especificadas antes
    pygame.display.set_caption("EulerPong")
    fondo = carga_imagen("fondo.jpg", IMG_DIR, alpha=False)
    #Cargamos el fondo
    bola = Pelota(IMG_DIR,Anchura_Pantalla,Altura_Pantalla)
    #Pasamos a una variable la clase Pelota
    jugador_1 = Barra(40, IMG_DIR, Anchura_Pantalla, Altura_Pantalla) 
    #El jugador 1 controla la barra de la izquierda, que está a 40 pixeles de 
    #la parte izquierda de la pantalla
    jugador_2 = Barra(Anchura_Pantalla - 40, IMG_DIR, Anchura_Pantalla, Altura_Pantalla)
    clock = pygame.time.Clock()
    #Creamos un reloj para que nos controle los fps
    """
    Para que el juego acepte que puedas pulsar muchas veces las teclas, 
    se necesita la función set_repeat, que toma dos argumentos:
       - numero de ms que tardas en mandar el primer evento
       - numero de ms que tienen que pasar entre que pasas el primer evento
         y el siguiente
    """    
    #-------------------------------------------------------------------------
    server2 = Client(userdata="Server")
    server2.connect(direccion)
    server2.subscribe('clients/EulerPong/'+password)
    server2.on_message = on_message_juego
    server2.loop_start()
    #Este cliente nos servirá para publicar aquí pues al ser un nuevo proceso
    #el que ejecuta esta función, el anterior se queda encargado de recibir
    #los mensajes
    #-------------------------------------------------------------------------
    while True:
        clock.tick(60) #Para que nunca se ejecute a mas de 60fps
        puntosJ = bola.update(server2, Anchura_Pantalla, Altura_Pantalla, puntosJugador_1, puntosJugador_2, password)
        jugador_1.rect.centery = barra_Y_J1J2[0][0]
        jugador_2.rect.centery = barra_Y_J1J2[0][1]
        bola.colision(jugador_1)
        bola.colision(jugador_2)
        puntosJugador_1 = puntosJ[0]
        puntosJugador_2 = puntosJ[1]
        """
        En el siguiente bucle se recorre la lista pygame.event.get, que es
        una lista con todos los eventos que registra pygame, por ejemplo
        cuando se presiona una tecla. 
        """
        for event in pygame.event.get(): 
            #lista con todos los eventos que registra pygame
            if event.type == pygame.QUIT: #Si se cierra la ventana
                pygame.quit()
                server2.publish('clients/EulerPong/'+password,"SERVIDOR_DESCONECTADO")
            elif event.type == pygame.KEYDOWN: #Si pulsas una tecla
                if event.key == K_ESCAPE: #Si pulsas Esc
                    pygame.quit()
                    server2.publish('clients/EulerPong/'+password,"SERVIDOR_DESCONECTADO")
        """
        Ahora vamos a poner que pasaría si alguno de los jugadores llega a
        10 puntos, lo que acabaría el juego:
        """
        if puntosJugador_1 == 10:
            server2.publish('clients/EulerPong/'+password,"J1.10")
            pygame.quit()

        elif puntosJugador_2 == 10:
            server2.publish('clients/EulerPong/'+password,"J2.10")
            pygame.quit()

        """
        Los siguientes comandos sirven para mostrar los Sprites y el fondo
        en la pantalla. 
        """
        pantalla.blit(fondo, (0, 0))
        pantalla.blit(bola.image, bola.rect)
        pantalla.blit(jugador_1.image,jugador_1.rect)
        pantalla.blit(jugador_2.image,jugador_2.rect)
        pantalla.blit(muestra_texto(str(puntosJugador_1)), (10,10))
        pantalla.blit(muestra_texto(str(puntosJugador_2)), (770,10))
        pygame.display.flip()
#-----------------------------------------------------------------------------

def main():
    #Aquí definimos los diccionarios, managers, semaforos, cliente, etc...
    manager = Manager()
    semaforo = Lock()
    semaforo_clientes = Lock()
    lista_procesos = []
    barra_Y_J1J2 = manager.list([(450 / 2,450 / 2)])
    dicc_conectados = manager.dict()
    print("ATENCION! Este Servidor solo funcionara si el servidor tiene el subcanal clients")
    print("Introduce la dirección del Servidor MQTT:")
    direccion = input()
    message = Message(barra_Y_J1J2, semaforo, semaforo_clientes, dicc_conectados, lista_procesos, direccion)
    server = Client(userdata="Server")
    server.enable_logger()
    server.on_message = message.on_message
    server.on_connect = on_connect
    server.on_subscribe = on_subscribe
    server.connect(direccion)
    server.subscribe('clients/EulerPong/#')
    server.loop_forever()

if __name__ == "__main__":
    main()
#-----------------------------------------------------------------------------

