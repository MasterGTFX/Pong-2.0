import sys, os.path, pygame, json, random, copy, threading, time
from math import sin, cos, radians, degrees
from pygame.locals import *

main_dir = os.path.split(os.path.abspath(__file__))[0]+"\\resources"
print(main_dir)
# initialization
pygame.init()
with open('config.json') as config_file:
    data = json.load(config_file)

# config
WINDOW_HEIGHT = data["WINDOW_HEIGHT"]
WINDOW_WIDTH = data["WINDOW_WIDTH"]
BACKGROUND_COLOR = tuple(data["BACKGROUND_COLOR"])
PADDLE_COLOR = tuple(data["PADDLE_COLOR"])
PADDLE_SPEED = data["PADDLE_SPEED"]
PADDLE_SIZE = data["PADDLE_SIZE"]
BALL_SPEED = data["BALL_SPEED"]
BALL_COLOR = tuple(data["BALL_COLOR"])
BALL_SIZE = data["BALL_SIZE"]
BASIC_FONT = pygame.font.SysFont(data["BASIC_FONT"][0], data["BASIC_FONT"][1])
BIG_FONT = pygame.font.SysFont(data["BASIC_FONT"][0], data["BASIC_FONT"][1])
SMALL_FONT = pygame.font.SysFont(data["BASIC_FONT"][0], data["BASIC_FONT"][1])
FONT_COLOR = tuple(data["FONT_COLOR"])
MAX_SCORE = data["MAX_SCORE"]
COMPUTER_LEVEL = data["COMPUTER_LEVEL"]
GUN_CD = data["GUN_CD"]
GUN_DURATION = data["GUN_DURATION"]

# game initialization
window = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), 0, 32, pygame.DOUBLEBUF)
pygame.display.set_caption('Pong Game')
background = pygame.Surface(window.get_size())
background = background.convert()
background.fill(BACKGROUND_COLOR)
window.blit(background, (0, 0))
pygame.display.flip()
clock = pygame.time.Clock()
tick = 60

# game constants
SCORE = [0, 0]
SCORED_NOW = False
PAUSED = False
GAME_OVER = False
GAME_STARTED = False
GAME_MODE = 1
PERKS = [[0, 0, 0], [0, 0, 0]]
LAST_TOUCH = 0
ONLINE = False



# game elements loading functions
class DummySound:
    def play(self, *args): pass


class DummyImg(pygame.Surface):
    pass


def load_sound(file):
    if not pygame.mixer: return DummySound()
    file = os.path.join(main_dir, file)
    try:
        sound = pygame.mixer.Sound(file)
        return sound
    except pygame.error:
        print('Warning, unable to load, %s' % file)
    except FileNotFoundError:
        print('Warning, unable to load, %s' % file)
    return DummySound()


def load_image(file):
    file = os.path.join(main_dir, file)
    try:
        image = pygame.image.load(file)
        return image
    except pygame.error:
        print('Warning, unable to load, %s' % file)
    except FileNotFoundError:
        print('Warning, unable to load, %s' % file)
    return DummyImg([64, 64])


class Paddle(pygame.sprite.Sprite):
    """
    Paddle class. Inherit init and update function. Update
    is called once per frame, sets paddle position and check
    if it collided with ball. If so it changes ball angle, based
    on collide point.
    """
    direction = 0
    speed = PADDLE_SPEED
    moving = False
    pos = [0, 0]
    gun_cd = 0
    gun = False
    bigger = False
    faster = False

    def __init__(self, player_number):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.player_number = player_number
        if PERKS[self.player_number][1] == 1:
            self.image = pygame.Surface([PADDLE_SIZE[0], PADDLE_SIZE[1] + 40])
            self.bigger = True
        else:
            self.image = pygame.Surface(PADDLE_SIZE)
        self.image.fill(PADDLE_COLOR)
        self.rect = self.image.get_rect()
        self.speed = PADDLE_SPEED
        if PERKS[self.player_number][0] == 1:
            self.speed += 4
            self.faster = True
        if PERKS[self.player_number][2] == 1:
            self.gun = True
        if self.player_number == 0:
            self.rect.centerx = window.get_rect().left
            self.rect.centerx += 50

        else:
            self.rect.centerx = window.get_rect().right
            self.rect.centerx -= 50
        self.rect.centery = window.get_rect().centery
        self.pos = [self.rect.x, self.rect.y]

    def update(self):
        global LAST_TOUCH
        if self.moving and not GAME_OVER and not PAUSED:
            if self.direction == 0 and self.rect.y > 5:
                self.rect.centery -= self.speed
            elif self.direction == 1 and self.rect.bottom < WINDOW_HEIGHT - 5:
                self.rect.centery += self.speed
            self.pos = [self.rect.x, self.rect.y]

    # shoot method can be used once per 5 seconds, so we need to use thread
    def shoot(self):
        if self.gun:
            if self.gun_cd == 0:
                shoot_music.play()
                Shot([self.rect.centerx, self.rect.centery])
                self.gun_cd = GUN_CD
                time.sleep(GUN_CD)
                self.gun_cd = 0

    def get_shot(self):
        get_shot_music.play()
        temp_speed = self.speed
        self.image.fill((0, 11, 30))
        self.speed = 1
        time.sleep(GUN_DURATION)
        self.image.fill(PADDLE_COLOR)
        self.speed = temp_speed


class ComputerPaddle(pygame.sprite.Sprite):
    """
    Computer paddle class. Pretty much same as normal paddle, but
    when ball is coming ball it moves depending of y-axis difference
    between its and ball position and percentage chance(to make it beatable)
    """
    ball = None
    direction = 0
    speed = PADDLE_SPEED
    pos = [0, 0]
    gun_cd = 0
    gun = False
    bigger = False
    faster = False

    def __init__(self, player_number, ball):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.ball = ball
        self.player_number = player_number
        if PERKS[self.player_number][1] == 1:
            self.image = pygame.Surface([PADDLE_SIZE[0], PADDLE_SIZE[1] + 40])
            self.bigger = True
        else:
            self.image = pygame.Surface(PADDLE_SIZE)
        self.image.fill(PADDLE_COLOR)
        self.rect = self.image.get_rect()
        self.speed = PADDLE_SPEED
        if PERKS[self.player_number][0] == 1:
            self.speed += 4
            self.faster = True
        if PERKS[self.player_number][2] == 1:
            self.gun = True
            x = threading.Thread(target=self.shoot, daemon=True)
            x.start()
        if self.player_number == 0:
            self.rect.centerx = window.get_rect().left
            self.rect.centerx += 50
        else:
            self.rect.centerx = window.get_rect().right
            self.rect.centerx -= 50
        self.rect.centery = window.get_rect().centery
        self.pos = [self.rect.x, self.rect.y]

    def update(self, *args):
        global LAST_TOUCH
        if not GAME_OVER and not PAUSED and LAST_TOUCH == 0 and random.randint(0, 100) < COMPUTER_LEVEL:
            if (self.pos[1] - random.randint(0, 10) > ball.pos[1]) and self.rect.y > 5:
                self.pos = project(self.pos, radians(90), self.speed)
            elif (self.pos[1] + random.randint(0, 10) < ball.pos[1]) and self.rect.bottom < WINDOW_HEIGHT - 5:
                self.pos = project(self.pos, radians(270), self.speed)
            self.rect.center = self.pos

    def shoot(self):
        while self.gun:
            if random.randint(1, 3) == 2:
                shoot_music.play()
                Shot([self.rect.centerx, self.rect.centery])
                time.sleep(GUN_CD)

    def get_shot(self):
        get_shot_music.play()
        temp_speed = self.speed
        self.image.fill((0, 11, 30))
        self.speed = 1
        time.sleep(GUN_DURATION)
        self.image.fill(PADDLE_COLOR)
        self.speed = temp_speed


def project(pos, angle, distance):
    """
    Returns tuple of pos projected distance at angle
    adjusted for pygame's y-axis.
    """
    return (pos[0] + (cos(angle) * distance),
            pos[1] - (sin(angle) * distance))


class Ball(pygame.sprite.Sprite):
    """
    Ball class. Inherited init and update function. Update
    is called once per frame and checks if ball collide with wall
    """
    speed = BALL_SPEED
    pos = (window.get_rect().centerx, window.get_rect().centery)
    moving = True

    def __init__(self, angle):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.angle = radians(angle)
        self.image = pygame.Surface(BALL_SIZE)
        self.image.fill(BALL_COLOR)
        self.rect = self.image.get_rect()
        self.rect.center = self.pos

    def update(self, *args):
        global SCORED_NOW
        if self.moving and not GAME_OVER and not PAUSED:
            # bal, hit horizontal wall
            if self.pos[1] < 2 or self.pos[1] > WINDOW_HEIGHT - 2:
                degree = degrees(self.angle)
                if (degree < 180):
                    self.angle = radians(360 - degree)
                else:
                    self.angle = radians(-degree)
            # ball hit vertical wall
            if self.pos[0] < 0:
                loose_music.play()
                # player 2 scores
                SCORE[1] += 1
                self.pos = (window.get_rect().centerx, window.get_rect().centery)
                self.angle = radians(180)
                SCORED_NOW = True
            if self.pos[0] > WINDOW_WIDTH:
                loose_music.play()
                # player 1 scores
                SCORE[0] += 1
                self.pos = (window.get_rect().centerx, window.get_rect().centery)
                self.angle = radians(0)
                SCORED_NOW = True
            self.pos = project(self.pos, self.angle, self.speed)
            self.rect.center = self.pos


class Shot(pygame.sprite.Sprite):
    speed = 25
    pos = [0, 0]

    def __init__(self, pos):
        pygame.sprite.Sprite.__init__(self, self.containers)
        self.image = pygame.Surface((25, 10))
        self.image.fill((0, 11, 30))
        self.rect = self.image.get_rect()
        self.pos = pos
        if pos[0] < WINDOW_WIDTH / 2:
            self.angle = radians(0)
            self.rect.center = [pos[0] + 25, pos[1]]
        else:
            self.angle = radians(180)
            self.rect.center = [pos[0] - 25, pos[1]]

    def update(self):
        if self.pos[0] < 0:
            self.kill()
        if self.pos[0] > WINDOW_WIDTH:
            self.kill()
        self.pos = project(self.pos, self.angle, self.speed)
        self.rect.center = self.pos


class Score(pygame.sprite.Sprite):
    def __init__(self):
        pygame.sprite.Sprite.__init__(self)
        self.image = BASIC_FONT.render(str(SCORE[0]) + "           " + str(SCORE[1]), True, FONT_COLOR,
                                       BACKGROUND_COLOR)
        self.rect = self.image.get_rect()
        self.rect.centerx = window.get_rect().centerx
        self.rect.y = 10

    def update(self, *args):
        self.image = BASIC_FONT.render(str(SCORE[0]) + "           " + str(SCORE[1]), True, FONT_COLOR,
                                       BACKGROUND_COLOR)


class Text(pygame.sprite.Sprite):
    def __init__(self, text, pos, font, text_color=FONT_COLOR, gamemode_text=0):
        pygame.sprite.Sprite.__init__(self)
        self.font = font
        self.text_color = text_color
        self.gamemode_text = gamemode_text
        self.pos = pos
        self.text = text
        self.image = font.render(text, True, text_color, BACKGROUND_COLOR)
        self.rect = self.image.get_rect()
        self.rect.centerx = pos[0]
        self.rect.centery = pos[1]

    def update(self, *args):
        self.image = self.font.render(self.text, True, self.text_color, BACKGROUND_COLOR)
        if 0 < self.gamemode_text == GAME_MODE:
            self.image = self.font.render(self.text, True, (139, 0, 0), BACKGROUND_COLOR)


class Image(pygame.sprite.Sprite):
    def __init__(self, img, pos, perk=[]):
        pygame.sprite.Sprite.__init__(self)
        self.pos = pos
        self.img = img
        self.perk = perk
        self.image = copy.copy(img)
        self.rect = self.image.get_rect()
        self.rect.centerx = pos[0]
        self.rect.centery = pos[1]

    def update(self, *args):
        self.image = copy.copy(self.img)
        if PERKS[self.perk[0]][self.perk[1]] == 1:
            self.image.blit(border_img, (0, 0))


# menu def
def menu():
    global GAME_MODE, GAME_STARTED, PERKS
    # All the assets(text and images) for menu declaration
    gametype_text = Text("Choose gamemode", [window.get_rect().centerx, window.get_rect().centery - 150], SMALL_FONT)
    choose_gametype1_text = Text("Player", [window.get_rect().centerx - 170, window.get_rect().centery], SMALL_FONT,
                                 gamemode_text=1)
    player1_perk1 = Image(boots_img, [choose_gametype1_text.rect.centerx - 64, choose_gametype1_text.rect.centery + 70],
                          [0, 0])
    player1_perk2 = Image(shield_img, [choose_gametype1_text.rect.centerx, choose_gametype1_text.rect.centery + 70],
                          [0, 1])
    player1_perk3 = Image(sword_img, [choose_gametype1_text.rect.centerx + 64, choose_gametype1_text.rect.centery + 70],
                          [0, 2])
    choose_gametype2_text = Text("Computer", [window.get_rect().centerx + 130, window.get_rect().centery], SMALL_FONT,
                                 gamemode_text=2)
    player2_perk1 = Image(boots_img, [choose_gametype2_text.rect.centerx - 64, choose_gametype1_text.rect.centery + 70],
                          [1, 0])
    player2_perk2 = Image(shield_img, [choose_gametype2_text.rect.centerx, choose_gametype1_text.rect.centery + 70],
                          [1, 1])
    player2_perk3 = Image(sword_img, [choose_gametype2_text.rect.centerx + 64, choose_gametype1_text.rect.centery + 70],
                          [1, 2])
    start_text = Text("START", [window.get_rect().centerx, window.get_rect().centery + 200], BIG_FONT, (255, 215, 0))
    all.add(gametype_text)
    all.add(choose_gametype1_text)
    all.add(choose_gametype2_text)
    all.add(player1_perk1)
    all.add(player2_perk1)
    all.add(player1_perk2)
    all.add(player2_perk2)
    all.add(player1_perk3)
    all.add(player2_perk3)
    all.add(start_text)
    while not GAME_STARTED:
        all.clear(window, background)
        all.update()
        for event in pygame.event.get():
            if event.type == QUIT:
                sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    pygame.quit()
                    sys.exit()
            if event.type == MOUSEBUTTONDOWN:
                if event.button == 1:
                    if choose_gametype1_text.rect.collidepoint(event.pos):
                        GAME_MODE = 1
                    if choose_gametype2_text.rect.collidepoint(event.pos):
                        GAME_MODE = 2
                    if start_text.rect.collidepoint(event.pos):
                        GAME_STARTED = True
                        all.empty()
                    if player1_perk1.rect.collidepoint(event.pos):
                        if PERKS[0][0] == 0:
                            PERKS[0][0] = 1
                        else:
                            PERKS[0][0] = 0
                    if player1_perk2.rect.collidepoint(event.pos):
                        if PERKS[0][1] == 0:
                            PERKS[0][1] = 1
                        else:
                            PERKS[0][1] = 0
                    if player1_perk3.rect.collidepoint(event.pos):
                        if PERKS[0][2] == 0:
                            PERKS[0][2] = 1
                        else:
                            PERKS[0][2] = 0
                    if player2_perk1.rect.collidepoint(event.pos):
                        if PERKS[1][0] == 0:
                            PERKS[1][0] = 1
                        else:
                            PERKS[1][0] = 0
                    if player2_perk2.rect.collidepoint(event.pos):
                        if PERKS[1][1] == 0:
                            PERKS[1][1] = 1
                        else:
                            PERKS[1][1] = 0
                    if player2_perk3.rect.collidepoint(event.pos):
                        if PERKS[1][2] == 0:
                            PERKS[1][2] = 1
                        else:
                            PERKS[1][2] = 0
                    clock.tick(tick)
        dirty = all.draw(window)
        pygame.display.update(dirty)


# assets loading (music + images)
background_music = load_sound("background.ogg")
hit_music = load_sound("hit.ogg")
game_over_music = load_sound("game_over.ogg")
loose_music = load_sound("loose.ogg")
shoot_music = load_sound("shoot.ogg")
get_shot_music = load_sound("get_shot.ogg")
border_img = load_image("border.png")
sword_img = load_image("sword.png")
boots_img = load_image("boots.png")
shield_img = load_image("shield.png")
# Initialize Game Groups
paddles = pygame.sprite.Group()
balls = pygame.sprite.Group()
shots = pygame.sprite.Group()
all = pygame.sprite.RenderUpdates()
# assign default groups to each sprite class
Paddle.containers = all, paddles
ComputerPaddle.containers = all, paddles
Ball.containers = all, balls
Shot.containers = all, shots
Score.containers = all
Text.containers = all
# menu loop
menu()
# game elements init
all.add(Score())
ball = Ball(180)
paddle1 = Paddle(0)
if GAME_MODE == 1:
    paddle2 = Paddle(1)
else:
    paddle2 = ComputerPaddle(1, ball)
temp = pygame.mouse.get_pos()
background_music.play(-1)
pygame.mouse.set_visible(False)
pygame.event.set_grab(True)
game_over_text = Text("GAME OVER", [window.get_rect().centerx, window.get_rect().centery - 50], BIG_FONT)
player1_win_text = Text("Player 1 Wins", [game_over_text.rect.centerx, game_over_text.rect.centery + 75],
                        BIG_FONT)
player2_win_text = Text("Player 2 Wins", [game_over_text.rect.centerx, game_over_text.rect.centery + 75],
                        SMALL_FONT)
reset_text = Text("Press (r) to reset", [game_over_text.rect.centerx, game_over_text.rect.centery + 150],
                  SMALL_FONT)
paused_text = Text("GAME PAUSED", [window.get_rect().centerx, 150], SMALL_FONT)
# game loop
while True:
    if ONLINE:
        pass
    if SCORED_NOW:
        if SCORE[0] > MAX_SCORE - 1:
            game_over_music.play()
            GAME_OVER = True
            all.add(game_over_text)
            all.add(player1_win_text)
            all.add(reset_text)
        elif SCORE[1] > MAX_SCORE - 1:
            game_over_music.play()
            GAME_OVER = True
            all.add(game_over_text)
            all.add(player2_win_text)
            all.add(reset_text)
        paddle1.rect.centery = window.get_rect().centery
        paddle2.rect.centery = window.get_rect().centery
        pygame.mouse.set_pos(window.get_rect().centerx, window.get_rect().centery)
        pygame.time.wait(1000)
        SCORED_NOW = False
    all.clear(window, background)
    all.update()
    for event in pygame.event.get():
        if event.type == QUIT:
            sys.exit()
        # paddle 2 control
        if event.type == KEYDOWN:
            # temp variable, for key up to not block going other direction
            up_temp = False
            down_temp = False
            if event.key == K_ESCAPE:
                pygame.quit()
                sys.exit()
            if event.key == ord('p'):
                if PAUSED:
                    PAUSED = False
                    all.remove(paused_text)
                else:
                    PAUSED = True
                    all.add(paused_text)
            if event.key == ord('r'):
                SCORE = [0, 0]
                if GAME_OVER:
                    GAME_OVER = False
                    all.remove(game_over_text)
                    all.remove(player1_win_text)
                    all.remove(player2_win_text)
                    all.remove(reset_text)
            if event.key == K_SPACE:
                x = threading.Thread(target=paddle2.shoot, daemon=True)
                x.start()
            if event.key == K_1:
                tick = 20
            if event.key == K_2:
                tick = 30
            if event.key == K_3:
                tick = 40
            if event.key == K_4:
                tick = 50
            if event.key == K_5:
                tick = 60
            if event.key == K_6:
                tick = 80
            if event.key == K_7:
                tick = 100
            if event.key == K_8:
                tick = 140
            if event.key == K_9:
                tick = 200
            if event.key == K_UP and not PAUSED and GAME_MODE == 1:
                paddle2.direction = 0
                paddle2.moving = True
                up_temp = True
            elif event.key == K_DOWN and not PAUSED and GAME_MODE == 1:
                paddle2.direction = 1
                paddle2.moving = True
                down_temp = True
        if event.type == KEYUP and GAME_MODE == 1:
            if event.key == K_UP:
                if not down_temp:
                    up_temp = False
                    paddle2.moving = False
            if event.key == K_DOWN:
                if not up_temp:
                    down_temp = False
                    paddle2.moving = False
        # Paddle 1 shooting
        if event.type == MOUSEBUTTONDOWN:
            if event.button == 1:
                x = threading.Thread(target=paddle1.shoot)
                x.start()
    # paddle 1 control
    mouse_diff = temp[1] - pygame.mouse.get_pos()[1]
    # so mouse wont get out of border
    if (pygame.mouse.get_pos()[0] < 5 or pygame.mouse.get_pos()[1] < 5 or pygame.mouse.get_pos()[
        0] > WINDOW_HEIGHT - 5 or pygame.mouse.get_pos()[1] < WINDOW_WIDTH - 5):
        pygame.mouse.set_pos(window.get_rect().centerx, window.get_rect().centery)
    if mouse_diff != 0 and not PAUSED:
        if mouse_diff > 0:
            paddle1.direction = 0
            paddle1.moving = True
        else:
            paddle1.direction = 1
            paddle1.moving = True
    else:
        paddle1.moving = False
    temp = pygame.mouse.get_pos()
    # detect collisions
    for paddle in paddles:
        for ball in pygame.sprite.spritecollide(paddle, balls, 0):
            hit_music.play()
            pos_hitted = ball.pos[1] - paddle.rect.centery
            if paddle.bigger:
                normalized_y = pos_hitted / ((PADDLE_SIZE[1] + 40) / 2)
            else:
                normalized_y = pos_hitted / (PADDLE_SIZE[1] / 2)
            bounce_angle = normalized_y * radians(75)
            # second paddle so we need to make ball go "other" way
            if paddle.rect.x > WINDOW_WIDTH / 2:
                bounce_angle = normalized_y * radians(75) + radians(180)
            ball.angle = bounce_angle
            LAST_TOUCH = paddle.player_number
        for bullet in pygame.sprite.spritecollide(paddle, shots, 0):
            bullet.kill()
            x = threading.Thread(target=paddle.get_shot)
            x.start()

    # draw the scene
    dirty = all.draw(window)
    pygame.display.update(dirty)
    pygame.display.flip()
    clock.tick(tick)
