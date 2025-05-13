import socket
import time
import json
import random
import importlib

pygame = importlib.import_module("pygame")

provod = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

provod.setblocking(False)

IP = ("localhost", 21124)

PORT_COUNT = 1

FPS = 60

DEFAULT_NICKNAME = "Player"

DEFAULT_SPAWN_POSITION = [0, 0]

DEFAULT_PLAYER_SPEED = 50

ticks = 0

delta_time = 0

last_time = 0

sleep_time = 0

is_running = True

provod.bind(IP)



class Servis:
	def __init__(self):
		self.clients = {}
		self.ticks = 0
		self.current_event = []
		self.events = {}
		self.is_pinging_clients = False
		self.clients_count = 0
		self.pinging_started_ticks = 0
		self.mercy_time = 20
		self.ping_cycle_activate_ticks = 3600
		self.current_house = None
		self.delta_time = 0
	def tick(self):			
		current_event = []
		
		client = None
		data, addr = None, None
		try:
				data, addr = provod.recvfrom(1024)
				if addr in self.clients:
					client = self.clients[addr]
					
				packet = data.decode()
				start_slace = packet.find("{")
				end_slace = packet.find("}{")
				if end_slace == -1:
					end_slace = packet.rfind("}")
				packet = packet[start_slace:end_slace+1]
				if not packet:
					packet = "{}"
				else:
					if client is not None:
						client.last_packet_time = time.time()
					response = json.loads(packet)
					
					events = response["event_bus"]
					for event in events:
						event_name = event[0]
						event_data = event[1]
						
						#print(event_name, event_data)
						
						if event_name == "New client":
							client = Client(addr)
							self.add_client(client)
							current_event.append(["Your ID", [client.id]])
						elif client is not None:
							if event_name == "Create room":
								room = Room(event_data[0], self.current_house)
								self.current_house.add_room(room)
							elif event_name == "Join room":
								room = self.current_house.get_room(event_data[0])
								new_player = Player(DEFAULT_NICKNAME, DEFAULT_SPAWN_POSITION, room)
								room.add_game_object(new_player)
								client.room = room
								client.player = new_player
								
								current_event.append(["Your player ID", [new_player.id]])
							elif event_name == "Leave room":
								if client.room is not None:
									client.room.remove_game_object(client.player)
									client.room = None
									client.player = None
							elif event_name == "Get condition of the room":
								if client.room is not None:
									condition_of_the_room = {"Name": client.room.name, "Game objects":[]}
									for game_object in client.room.game_objects:
										condition_of_the_room["Game objects"].append([game_object.type, game_object.id, game_object.position])
								
								current_event.append(["Your condition of the room", [condition_of_the_room]])
							elif event_name == "Client alive":
								current_event.append(["OK", [True]])
							elif event_name == "Game object moved":
								if event_data[0] == client.player.id:
									client.player.move(event_data[1])
		except BlockingIOError or ConnectionResetError:
				pass

				
		current_event += self.current_house.events
			
		if client is not None:
			if client.room is not None:
				current_event += client.room.events


		if current_event and addr is not None:
					try:
						request = {"event_bus": current_event, "ticks": self.ticks}
						packet = json.dumps(request)
						data = packet.encode()
						provod.sendto(data, addr)
						#print(request)
					except OSError:
						pass
						
						
		removable_clients = []
		for client_addr in self.clients:
			client = self.clients[client_addr]
			if time.time() - client.last_packet_time > self.mercy_time:
				removable_clients.append(client)
				
		for removable_client in removable_clients:
				self.remove_client(removable_client)
			
			
		self.ticks += 1
	
	def add_client(self, client):
		self.clients.update({client.addr:client})
		self.clients_count += 1
		print("add client")
	
	def remove_client(self, client):
		self.clients.pop(client.addr)
		self.clients_count -= 1
		if client.room is not None:
			client.room.game_objects.remove(client.player)
		print("delete client")
				
class Client:
	def __init__(self, addr):
		self.addr = addr
		self.last_packet_time = time.time()
		self.player = None
		self.room = None
		self.id = random.randint(0, 1000)

class House:
	def __init__(self, servis):
		self.rooms = {}
		self.servis = servis
		self.events = []
	def get_room(self, name):
		return self.rooms[name]
	def add_room(self, room):
		room.house = self
		self.rooms.update({room.name:room})
		self.events.append(["Add room", [room.name]])
	def remove_room(sel, room):
		self.rooms.pop(room.name)
		self.events.append(["Remove room", [room.name]])
	def tick(self):
		self.events = []
		for room in list(self.rooms.values()):
			room.update()

class Room:
	def __init__(self, name, house):
		self.name = name
		self.game_objects = []
		self.house = house
		self.events = []
		self.map = "Stone Island"
	def add_game_object(self, game_object):
		self.game_objects.append(game_object)
		self.events.append(["Add game object", [game_object.type, game_object.id, game_object.position]])
	def remove_game_object(self, game_object):
		self.events.append(["Remove game object", [game_object.id]])
		self.game_objects.remove(game_object)
	def update(self):
		self.events = []
		for game_object in self.game_objects:
			game_object.update()
			self.events += game_object.events
			
class Player:
	def __init__(self, nickname, position, room):
		self.type = "Player"
		self.nickname = nickname
		self.position = position
		self.rect = pygame.Rect(self.position[0], self.position[1], 50, 50)
		self.velocity = [0, 0]
		self.speed = 50
		self.room = room
		self.id = random.randint(0, 1000)
		self.events = []
	def update(self):
		self.rect.x = self.position[0]
		self.rect.y = self.position[1]
	def move(self, direction):
		self.velocity[0] = direction[0]
		self.velocity[1] = direction[1]
		
		self.position[0] += self.speed * self.velocity[0] * self.room.house.servis.delta_time
		self.rect.x = self.position[0]
		
		game_objects = [game_object for game_object in self.room.game_objects]
		rects = [game_object.rect for game_object in game_objects]
		rects.remove(self.rect)
		collided_rect_index = self.rect.collidelist(rects)
		try:
		  	collided_rect = rects[collided_rect_index]
		except IndexError:
			pass
		
		if collided_rect_index != -1:
				if self.velocity[0] > 0:
					self.rect.right = collided_rect.left
				elif self.velocity[0] < 0:
					self.rect.left = collided_rect.right
					
				self.position[0] = self.rect.x
		
		self.position[1] += self.speed * self.velocity[1] * self.room.house.servis.delta_time
		self.rect.y = self.position[1]
		
		game_objects = [game_object for game_object in self.room.game_objects]
		rects = [game_object.rect for game_object in game_objects]
		rects.remove(self.rect)
		collided_rect_index = self.rect.collidelist(rects)
		try:
			collided_rect = rects[collided_rect_index]
		except IndexError:
			pass
		if collided_rect_index != -1:
				if self.velocity[1] > 0:
					self.rect.bottom = collided_rect.top
				elif self.velocity[1] < 0:
					self.rect.top = collided_rect.bottom
					
				self.position[1] = self.rect.y
					
		self.events.append(["Game object moved", [self.id, self.position]])
		
		self.velocity = [0, 0]


servis = Servis()

house = House(servis)

servis.current_house = house

while is_running:
	house.tick()
	
	servis.tick()

	delta_time = time.time()-last_time
	
	servis.delta_time = delta_time

	last_time = time.time()

	sleep_time = 1/FPS - delta_time

	if sleep_time <= 0:
		sleep_time = 0

	time.sleep(sleep_time)
	
	ticks += 1
	
provod.close()
