# -*- coding: utf-8 -*-

import pygame
from pygame.locals import *
#te importa constantes de pygame que reconocen teclas del teclado
import os
import sys #para que salga del juego si se cierra la ventana
from paho.mqtt.client import Client
import time
from multiprocessing import Process
from multiprocessing import Manager
from multiprocessing import Lock
#--------------------------------------


def on_connect(client, userdata, flags, rc):
    if rc == 0:
        time.sleep(1)
        print("Conectado al Broker con exito!")
        time.sleep(1)
    else:
        print("No se pudo establecer conexión con el Broker: codigo rc=", rc)
        
def on_subscribe(client, userdata, mid, granted_qos):
    print("Conectado al Channel con exito!") 
    time.sleep(1)
    print("Esperando al Servidor...")
    time.sleep(1)

    """
    on_message está definido como una clase por la facilidad que supone
    su implementacion para transferir monitores y semaforos que entrarian en 
    juego al recibir un mensaje, y así poder pasarlos a más de un proceso.
    """
    
class Message:

    def __init__(self, bola_coord, puntos, password, semaforo, cerrar_conexion, barra_Y_J1J2, direccion):
        self.bola_coord = bola_coord
        self.puntos = puntos
        self.semaforo = semaforo
        self.password = password
        self.cerrar_conexion = cerrar_conexion
        self.barra_Y_J1J2 = barra_Y_J1J2     
        self.direccion = direccion
        #definimos los parametros en la inicializacion de la clase, que haremos
        #en el main, y los pasamos a on.message
        
    def on_message(self, client, userdata, msg):
        mensaje = str(msg.payload.decode("utf-8"))
        bola_coord = self.bola_coord
        semaforo = self.semaforo
        puntos = self.puntos
        password = self.password
        cerrar_conexion = self.cerrar_conexion
        barra_Y_J1J2 = self.barra_Y_J1J2
        direccion = self.direccion

        if mensaje == "SERVIDOR_DESCONECTADO":
            print("El Servidor se ha desconectado.")
            sys.exit(0)
            
        if mensaje == "CLIENTE_DESCONECTADO":
            print("Tu o tu rival os habeis desconectado.")
            sys.exit(0)
            
        if mensaje == "NOBODY":
            print("El código introducido no corresponde a ninguna sala. Vuelve a intentarlo.")
            sys.exit(0)
            
        if mensaje[0:18] == "SERVIDOR_CONECTADO":
            #cerrar_conexion sirve para no dejar ejecutar el mismo juego en 
            #el cliente dos veces.
            if cerrar_conexion == False:
                cerrar_conexion = True
                print("Servidor conectado!")
                and_symbol = mensaje.index("&")
                userdata_1 = mensaje[19:and_symbol]
                userdata_2 = mensaje[and_symbol+1:]
                time.sleep(1)
                if userdata[-7:] == 'client2':
                    p = Process(target=juego_client_2, args=(bola_coord, puntos, password, semaforo, userdata_1, userdata_2, barra_Y_J1J2, direccion))
                    p.start()
                    time.sleep(4)
                elif userdata[-7:] == 'client1':
                    q = Process(target=juego_client_1, args=(bola_coord, puntos, password, semaforo, userdata_1, userdata_2, barra_Y_J1J2, direccion))
                    q.start()
                #realizamos procesos distintos segun el cliente (cliente_1
                #se conecta a una sala existente y cliente_2 crea la sala)
                print("El juego empieza en...")
                i = 5
                while i != 0:
                    print(i,"!")
                    time.sleep(1)
                    i -= 1
        #Aquí se detallan todos los mensajes que pueden llegar para actualizar
        #el juego.
                    
        if mensaje[0:3] == 'bc.': #mensaje con las coordenadas de la pelota
            index_coma = mensaje.index(",")
            index_final = mensaje.index(")")
            bola_x = int(mensaje[4:index_coma])
            bola_y = int(mensaje[index_coma+1:index_final]) 
            semaforo.acquire()
            bola_coord.append((bola_x,bola_y))
            semaforo.release()
            
        if mensaje[0:3] == 'J1.': #mensaje con los puntos del Jugador_1
            puntos_J1 = int(mensaje[3:])
            semaforo.acquire()
            puntos_J2 = puntos[0][1]
            puntos.append((puntos_J1, puntos_J2))
            puntos.pop(0)
            semaforo.release()
            
        if mensaje[0:3] == 'J2.':#mensaje con los puntos del Jugador_2
            puntos_J2 = int(mensaje[3:])
            semaforo.acquire()
            puntos_J1 = puntos[0][0]
            puntos.append((puntos_J1, puntos_J2))
            puntos.pop(0)
            semaforo.release()
            
        if mensaje[0:3] == "J2B": #mensaje con las coordenadas de la barra
            #del Jugador_2
            barra_J2 = int(mensaje[3:])
            semaforo.acquire()
            barra_J1 = barra_Y_J1J2[0][0]
            barra_Y_J1J2.append((barra_J1,barra_J2))
            barra_Y_J1J2.pop(0)
            semaforo.release()
            
        if mensaje[0:3] == "J1B":#mensaje con las coordenadas de la barra
            #del Jugador_2            
            barra_J1 = int(mensaje[3:])
            semaforo.acquire()
            barra_J2 = barra_Y_J1J2[0][1]
            barra_Y_J1J2.append((barra_J1,barra_J2))
            barra_Y_J1J2.pop(0)
            semaforo.release()
 
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
        
    def update(self, bola_coord, semaforo):
        if len(bola_coord) >= 1:
            semaforo.acquire()
            (self.rect.centerx,self.rect.centery) = bola_coord[0]
            bola_coord.pop(0)
            semaforo.release()
            
        """
        Esta función se encarga de hacer avanzar la pelota y que rebote cuando
        llegue al límite de la pantalla.
        """ 

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
        
    def control_barra(self, Anchura_Pantalla, Altura_Pantalla):
        if self.rect.bottom >= Altura_Pantalla:
            self.rect.bottom = Altura_Pantalla
        elif self.rect.top <= 0:
            self.rect.top = 0
        #Aquí controlamos que la barra no se salga de la pantalla

#-----------------------------------------------------------------------------


def juego_client_1(bola_coord, puntos, password, semaforo, userdata_1, userdata_2, barra_Y_J1J2, direccion):
    puntosJugador_1 = puntos[0][0]
    puntosJugador_2 = puntos[0][1]
    Anchura_Pantalla = 800
    Altura_Pantalla = 450

    IMG_DIR = "IMAGENES"
    #es la carpeta donde van a estar las imágenes
    
    #------------------------------------------------------------------------
    pygame.init()
    pygame.mixer.init()
    pygame.font.init()
    #Ejecutamos pygame
    pantalla = pygame.display.set_mode((Anchura_Pantalla, Altura_Pantalla))
    #Creamos pantalla con las dimensiones especificadas antes
    pygame.display.set_caption("EulerPong")
    fondo = carga_imagen("fondo.jpg", IMG_DIR, alpha=False)
    fondo_ganador = carga_imagen("fondo_ganador.jpg", IMG_DIR, alpha=False)
    fondo_perdedor = carga_imagen("fondo_perdedor.jpg", IMG_DIR, alpha=False)
    
    texto_J1 = muestra_texto(userdata_1)
    texto_J2 = muestra_texto(userdata_2)
    texto_pos_J1 = texto_J1.get_rect(center=(200,25))
    texto_pos_J2 = texto_J2.get_rect(center=(600,25))
    
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
    pygame.key.set_repeat(1,25)
    pygame.mouse.set_visible(False) 
    #Vamos a controlar las barras también por ratón. Esto que hace que no se
    #vea el ratón en la pantalla
    #-------------------------------------------------------------------------
    client_1_juego = Client(userdata="Cliente_1_juego")
    client_1_juego.connect(direccion)
    client_1_juego.subscribe('clients/EulerPong/'+password)
    client_1_juego.loop_start()
    #-------------------------------------------------------------------------
    #time.sleep(5)
    #'------------------------------------------------------------------------
    while True:
        clock.tick(60) #Para que nunca se ejecute a mas de 60fps
        pos_mouse = pygame.mouse.get_pos() 
        #Registramos posicion del raton, lo que devuelve una tupla con las 
        #coordenadas x e y
        mov_mouse = pygame.mouse.get_rel()
        #Devuelve cuando se ha movido el mouse desde la última consulta que
        #realizó. Si no se ha movido, devuelve (0,0)
        bola.update(bola_coord, semaforo)
        puntosJugador_1 = puntos[0][0]
        puntosJugador_2 = puntos[0][1]
        jugador_1.control_barra(Anchura_Pantalla, Altura_Pantalla)
        jugador_2.rect.centery = barra_Y_J1J2[0][1]

        """
        En el siguiente bucle se recorre la lista pygame.event.get, que es
        una lista con todos los eventos que registra pygame, por ejemplo
        cuando se presiona una tecla. 
        """
        for event in pygame.event.get(): 
            #lista con todos los eventos que registra pygame
            if event.type == pygame.QUIT: #Si se cierra la ventana
                client_1_juego.publish('clients/EulerPong/'+password,"CLIENTE_DESCONECTADO")
                pygame.quit()
                sys.exit(0)
            elif event.type == pygame.KEYDOWN: #Si pulsas una tecla
                if event.key == K_UP:
                    jugador_1.rect.centery -= 5
                    client_1_juego.publish('clients/EulerPong/'+password,"J1B"+str(jugador_1.rect.centery))
                elif event.key == K_DOWN: 
                    jugador_1.rect.centery += 5
                    client_1_juego.publish('clients/EulerPong/'+password,"J1B"+str(jugador_1.rect.centery))
                elif event.key == K_ESCAPE: #Si pulsas Esc
                    client_1_juego.publish('clients/EulerPong/'+password,"CLIENTE_DESCONECTADO")
                    pygame.quit()
                    sys.exit(0)
       
            elif event.type == pygame.KEYUP: #Si sueltas una tecla
                if event.key == K_UP:
                    jugador_1.rect.centery += 0
                    jugador_2.rect.centery += 0
                elif event.key == K_DOWN:
                    jugador_1.rect.centery += 0
                    jugador_1.rect.centery += 0
            
            #Ahora hay que dar respuesta al ratón:
            elif mov_mouse[1] != 0: #El ratón se ha movido en coordenada "y"
                jugador_1.rect.centery = pos_mouse[1]
                client_1_juego.publish('clients/EulerPong/'+password,"J1B"+str(jugador_1.rect.centery))
        """
        Ahora vamos a poner que pasaría si alguno de los jugadores llega a
        10 puntos, lo que acabaría el juego:
        """
        if puntosJugador_1 == 10:
            while True:
                pantalla.blit(fondo_ganador, (0,0))
                pygame.display.flip()
                for event in pygame.event.get(): 
                    if event.type == pygame.QUIT: #Si se cierra la ventana
                        pygame.quit()
                        sys.exit(0)                    
                    if event.type == pygame.KEYDOWN: #Si pulsas una tecla
                        if event.key == K_ESCAPE: #Si pulsas Esc
                            pygame.quit()
                            sys.exit(0)
        elif puntosJugador_2 == 10:
            while True:
                pantalla.blit(fondo_perdedor, (0,0)) 
                pygame.display.flip()
                for event in pygame.event.get(): 
                    if event.type == pygame.QUIT: #Si se cierra la ventana
                        pygame.quit()
                        sys.exit(0)                    
                    if event.type == pygame.KEYDOWN: #Si pulsas una tecla
                        if event.key == K_ESCAPE: #Si pulsas Esc
                            pygame.quit()
                            sys.exit(0)                   

        """
        Los siguientes comandos sirven para mostrar los Sprites y el fondo
        en la pantalla. 
        """
        pantalla.blit(fondo, (0, 0))
        pantalla.blit(bola.image, bola.rect)
        pantalla.blit(jugador_1.image,jugador_1.rect)
        pantalla.blit(jugador_2.image,jugador_2.rect)
        pantalla.blit(muestra_texto("VS"), (382,10))
        pantalla.blit(muestra_texto(str(puntosJugador_1)),(10,10))
        pantalla.blit(muestra_texto(str(puntosJugador_2)),(770,10))
        pantalla.blit(texto_J1,texto_pos_J1)
        pantalla.blit(texto_J2,texto_pos_J2)
        pygame.display.flip()

#-----------------------------------------------------------------------------

def juego_client_2(bola_coord, puntos, password, semaforo, userdata_1, userdata_2, barra_Y_J1J2, direccion):
    puntosJugador_1 = puntos[0][0]
    puntosJugador_2 = puntos[0][1]
    Anchura_Pantalla = 800
    Altura_Pantalla = 450

    IMG_DIR = "IMAGENES"
    #es la carpeta donde van a estar las imágenes
    
    #------------------------------------------------------------------------
    pygame.init()
    pygame.mixer.init()
    pygame.font.init()
    #Ejecutamos pygame
    pantalla = pygame.display.set_mode((Anchura_Pantalla, Altura_Pantalla))
    #Creamos pantalla con las dimensiones especificadas antes
    pygame.display.set_caption("EulerPong")
    fondo = carga_imagen("fondo.jpg", IMG_DIR, alpha=False)
    fondo_ganador = carga_imagen("fondo_ganador.jpg", IMG_DIR, alpha=False)
    fondo_perdedor = carga_imagen("fondo_perdedor.jpg", IMG_DIR, alpha=False)
    #Cargamos el fondo
    bola = Pelota(IMG_DIR,Anchura_Pantalla,Altura_Pantalla)
    #Pasamos a una variable la clase Pelota
    jugador_1 = Barra(40, IMG_DIR, Anchura_Pantalla, Altura_Pantalla) 
    #El jugador 1 controla la barra de la izquierda, que está a 40 pixeles de 
    #la parte izquierda de la pantalla
    jugador_2 = Barra(Anchura_Pantalla - 40, IMG_DIR, Anchura_Pantalla, Altura_Pantalla)
    clock = pygame.time.Clock()
    
    texto_J1 = muestra_texto(userdata_1)
    texto_J2 = muestra_texto(userdata_2)
    texto_pos_J1 = texto_J1.get_rect(center=(200,25))
    texto_pos_J2 = texto_J2.get_rect(center=(600,25))
    #Creamos un reloj para que nos controle los fps
    """
    Para que el juego acepte que puedas pulsar muchas veces las teclas, 
    se necesita la función set_repeat, que toma dos argumentos:
       - numero de ms que tardas en mandar el primer evento
       - numero de ms que tienen que pasar entre que pasas el primer evento
         y el siguiente
    """    
    pygame.key.set_repeat(1,25)
    pygame.mouse.set_visible(False) 
    #Vamos a controlar las barras también por ratón. Esto que hace que no se
    #vea el ratón en la pantalla
    #-------------------------------------------------------------------------
    client_2_juego = Client(userdata="Cliente_2_juego")
    client_2_juego.connect(direccion)
    client_2_juego.subscribe('clients/EulerPong/'+password)
    client_2_juego.loop_start()
    #-------------------------------------------------------------------------
    #time.sleep(5)
    #'------------------------------------------------------------------------
    while True:
        clock.tick(60) #Para que nunca se ejecute a mas de 60fps
        pos_mouse = pygame.mouse.get_pos() 
        #Registramos posicion del raton, lo que devuelve una tupla con las 
        #coordenadas x e y
        mov_mouse = pygame.mouse.get_rel()
        #Devuelve cuando se ha movido el mouse desde la última consulta que
        #realizó. Si no se ha movido, devuelve (0,0)
        bola.update(bola_coord, semaforo)
        puntosJugador_1 = puntos[0][0]
        puntosJugador_2 = puntos[0][1]
        jugador_1.rect.centery = barra_Y_J1J2[0][0]
        jugador_2.control_barra(Anchura_Pantalla, Altura_Pantalla)

        """
        En el siguiente bucle se recorre la lista pygame.event.get, que es
        una lista con todos los eventos que registra pygame, por ejemplo
        cuando se presiona una tecla. 
        """
        for event in pygame.event.get(): 
            #lista con todos los eventos que registra pygame
            if event.type == pygame.QUIT: #Si se cierra la ventana
                client_2_juego.publish('clients/EulerPong/'+password,"CLIENTE_DESCONECTADO")
                pygame.quit()
                sys.exit(0)
            elif event.type == pygame.KEYDOWN: #Si pulsas una tecla
                if event.key == K_UP:
                    jugador_2.rect.centery -= 5
                    client_2_juego.publish('clients/EulerPong/'+password,"J2B"+str(jugador_2.rect.centery))
                elif event.key == K_DOWN: 
                    jugador_2.rect.centery += 5
                    client_2_juego.publish('clients/EulerPong/'+password,"J2B"+str(jugador_2.rect.centery))
                elif event.key == K_ESCAPE: #Si pulsas Esc
                    client_2_juego.publish('clients/EulerPong/'+password,"CLIENTE_DESCONECTADO")
                    pygame.quit()
                    sys.exit(0)
       
            elif event.type == pygame.KEYUP: #Si sueltas una tecla
                if event.key == K_UP:
                    jugador_1.rect.centery += 0
                    jugador_2.rect.centery += 0
                elif event.key == K_DOWN:
                   jugador_1.rect.centery += 0
                   jugador_1.rect.centery += 0
            
            #Ahora hay que dar respuesta al ratón:
            elif mov_mouse[1] != 0: #El ratón se ha movido en coordenada "y"
                jugador_2.rect.centery = pos_mouse[1]
                client_2_juego.publish('clients/EulerPong/'+password,"J2B"+str(jugador_2.rect.centery))
        """
        Ahora vamos a poner que pasaría si alguno de los jugadores llega a
        10 puntos, lo que acabaría el juego:
        """
        if puntosJugador_1 == 10:
            while True:
                pantalla.blit(fondo_perdedor, (0,0))
                pygame.display.flip()
                for event in pygame.event.get(): 
                    if event.type == pygame.QUIT: #Si se cierra la ventana
                        pygame.quit()
                        sys.exit(0)                    
                    if event.type == pygame.KEYDOWN: #Si pulsas una tecla
                        if event.key == K_ESCAPE: #Si pulsas Esc
                            pygame.quit()
                            sys.exit(0)
        elif puntosJugador_2 == 10:
            while True:
                pantalla.blit(fondo_ganador, (0,0)) 
                pygame.display.flip()
                for event in pygame.event.get(): 
                    if event.type == pygame.QUIT: #Si se cierra la ventana
                        pygame.quit()
                        sys.exit(0)                    
                    if event.type == pygame.KEYDOWN: #Si pulsas una tecla
                        if event.key == K_ESCAPE: #Si pulsas Esc
                            pygame.quit()
                            sys.exit(0)                   

        """
        Los siguientes comandos sirven para mostrar los Sprites y el fondo
        en la pantalla. 
        """
        pantalla.blit(fondo, (0, 0))
        pantalla.blit(bola.image, bola.rect)
        pantalla.blit(jugador_1.image,jugador_1.rect)
        pantalla.blit(jugador_2.image,jugador_2.rect)
        pantalla.blit(muestra_texto("VS"), (382,10))
        pantalla.blit(muestra_texto(str(puntosJugador_1)),(10,10))
        pantalla.blit(muestra_texto(str(puntosJugador_2)),(770,10))
        pantalla.blit(texto_J1,texto_pos_J1)
        pantalla.blit(texto_J2,texto_pos_J2)
        pygame.display.flip()

#-----------------------------------------------------------------------------

def main(): #se introducen las opciones para crear o unirse a sala
    f_intro = open('intro.txt','r')
    intro = f_intro.read()
    print(intro)
    f_intro.close
    
    apodo_client = input()
    
    f_intro2 = open('intro2.txt', 'r')
    intro2 = f_intro2.read()
    print(intro2)
    f_intro2.close
    
    direccion = input()
    
    f_intro3 = open('intro3.txt', 'r')
    intro3 = f_intro3.read()
    print(intro3)
    f_intro3.close
    
    opcion = input()
    
    if opcion == "C" or opcion == "c": #opcion crear sala
        print('Muy bien! Ahora crea un codigo para la sala:')     
        
        password = input()        
        print('Ahora se creará la partida. Asegurate de pasar la contraseña correcta a tu rival para jugar')
        time.sleep(2)
        manager = Manager()
        bola_coord = manager.list([(800 / 2, 450 / 2)])
        puntos = manager.list([(0,0)])
        semaforo = Lock()
        cerrar_conexion = False
        barra_Y_J1J2 = manager.list([(450 / 2,450 / 2)])
        message = Message(bola_coord, puntos, password, semaforo, cerrar_conexion, barra_Y_J1J2, direccion)
        
        client_2 = Client(userdata=(apodo_client+".client2"))
        client_2.enable_logger()
        client_2.on_message = message.on_message
        client_2.on_connect = on_connect
        client_2.on_subscribe = on_subscribe
        client_2.connect(direccion)
        client_2.subscribe('clients/EulerPong/'+password)
        client_2.publish('clients/EulerPong/'+password, apodo_client + '.Cliente_2.conectado')
        client_2.loop_forever()
        
    elif opcion == "U" or opcion == "u": #opcion unirse a sala
        print('Introduce el código de la sala:')
        
        password = input()
        print('Buscando salas con este codigo...')
        manager = Manager()
        bola_coord = manager.list([(800 / 2, 450 / 2)])
        puntos = manager.list([(0,0)])
        semaforo = Lock()
        cerrar_conexion = False
        barra_Y_J1J2 = manager.list([(450 / 2,450 / 2)])
        message = Message(bola_coord, puntos, password, semaforo, cerrar_conexion, barra_Y_J1J2, direccion)
        
        client_1 = Client(userdata=apodo_client+".client1")
        client_1.enable_logger()
        client_1.on_message = message.on_message
        client_1.on_connect = on_connect
        client_1.on_subscribe = on_subscribe
        client_1.connect(direccion)
        client_1.subscribe('clients/EulerPong/'+password)
        client_1.publish('clients/EulerPong/'+password, apodo_client + '.Cliente_1.conectado')
        client_1.loop_forever()
    else:
        print('Parece que no has elegido ninguna opcion. ¡Hasta pronto!')
        sys.exit(0)
    
    
if __name__ == "__main__":
    main()
    
