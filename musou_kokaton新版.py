import math
import os
import random
import sys
import time
import pygame as pg

WIDTH, HEIGHT = 1600, 900  # ゲームウィンドウの幅，高さ
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def check_bound(obj_rct:pg.Rect) -> tuple[bool, bool]:
    """
    Rectの画面内外判定用の関数
    引数：こうかとんRect，または，爆弾Rect，またはビームRect
    戻り値：横方向判定結果，縦方向判定結果（True：画面内／False：画面外）
    """
    yoko, tate = True, True
    if obj_rct.left < 0 or WIDTH < obj_rct.right:  # 横方向のはみ出し判定
        yoko = False
    if obj_rct.top < 0 or HEIGHT < obj_rct.bottom:  # 縦方向のはみ出し判定
        tate = False
    return yoko, tate


def calc_orientation(org: pg.Rect, dst: pg.Rect) -> tuple[float, float]:
    """
    orgから見て，dstがどこにあるかを計算し，方向ベクトルをタプルで返す
    引数1 org：爆弾SurfaceのRect
    引数2 dst：こうかとんSurfaceのRect
    戻り値：orgから見たdstの方向ベクトルを表すタプル
    """
    x_diff, y_diff = dst.centerx-org.centerx, dst.centery-org.centery
    norm = math.sqrt(x_diff**2+y_diff**2)
    return x_diff/norm, y_diff/norm


class Bird(pg.sprite.Sprite):
    """
    ゲームキャラクター（こうかとん）に関するクラス
    """
    delta = {  # 押下キーと移動量の辞書
        pg.K_UP: (0, -1),
        pg.K_DOWN: (0, +1),
        pg.K_LEFT: (-1, 0),
        pg.K_RIGHT: (+1, 0),
    }


    def __init__(self, num: int, xy: tuple[int, int]):
        """
        こうかとん画像Surfaceを生成する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 xy：こうかとん画像の位置座標タプル
        """
        super().__init__()
        img0 = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 2.0)
        img = pg.transform.flip(img0, True, False)  # デフォルトのこうかとん
        self.imgs = {
            (+1, 0): img,  # 右
            (+1, -1): pg.transform.rotozoom(img, 45, 1.0),  # 右上
            (0, -1): pg.transform.rotozoom(img, 90, 1.0),  # 上
            (-1, -1): pg.transform.rotozoom(img0, -45, 1.0),  # 左上
            (-1, 0): img0,  # 左
            (-1, +1): pg.transform.rotozoom(img0, 45, 1.0),  # 左下
            (0, +1): pg.transform.rotozoom(img, -90, 1.0),  # 下
            (+1, +1): pg.transform.rotozoom(img, -45, 1.0),  # 右下
        }
        self.dire = (+1, 0)
        self.image = self.imgs[self.dire]
        self.rect = self.image.get_rect()
        self.rect.center = xy
        self.speed = 10
        self.state = "normal"
        self.hyper_life = 0

    
    def change_img(self, num: int, screen: pg.Surface):
        """
        こうかとん画像を切り替え，画面に転送する
        引数1 num：こうかとん画像ファイル名の番号
        引数2 screen：画面Surface
        """
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/{num}.png"), 0, 2.0)
        screen.blit(self.image, self.rect)

    def update(self, key_lst: list[bool], screen: pg.Surface):
        """
        押下キーに応じてこうかとんを移動させる
        引数1 key_lst：押下キーの真理値リスト
        引数2 screen：画面Surface
        """
        self.speed = 10
        sum_mv = [0, 0]
        if self.state == "hyper":
            self.image = pg.transform.laplacian(self.image)
            self.hyper_life -= 1
            if self.hyper_life <= 0:
                self.state = "normal"
                self.image = pg.transform.laplacian(self.image)
        for k, mv in __class__.delta.items():
            if key_lst[k]:
                sum_mv[0] += mv[0]
                sum_mv[1] += mv[1]
        if key_lst[pg.K_LSHIFT]:
            self.speed = 20
        self.rect.move_ip(self.speed*sum_mv[0], self.speed*sum_mv[1])
        if check_bound(self.rect) != (True, True):
            self.rect.move_ip(-self.speed*sum_mv[0], -self.speed*sum_mv[1])
        if not (sum_mv[0] == 0 and sum_mv[1] == 0):
            self.dire = tuple(sum_mv)
            self.image = self.imgs[self.dire]
        screen.blit(self.image, self.rect)


class Bomb(pg.sprite.Sprite):
    """
    爆弾に関するクラス
    """
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0), (255, 0, 255), (0, 255, 255)]

    def __init__(self, emy: "Enemy", bird: Bird):
        """
        爆弾円Surfaceを生成する
        引数1 emy：爆弾を投下する敵機
        引数2 bird：攻撃対象のこうかとん
        """
        super().__init__()
        rad = random.randint(10, 50)  # 爆弾円の半径：10以上50以下の乱数
        self.image = pg.Surface((2*rad, 2*rad))
        color = random.choice(__class__.colors)  # 爆弾円の色：クラス変数からランダム選択
        pg.draw.circle(self.image, color, (rad, rad), rad)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect()
        # 爆弾を投下するemyから見た攻撃対象のbirdの方向を計算
        self.vx, self.vy = calc_orientation(emy.rect, bird.rect)  
        self.rect.centerx = emy.rect.centerx
        self.rect.centery = emy.rect.centery+emy.rect.height/2
        self.speed = 6
        self.state = "active"

    def update(self):
        """
        爆弾を速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Beam(pg.sprite.Sprite):
    """
    ビームに関するクラス
    """
    def __init__(self, bird: Bird):
        """
        ビーム画像Surfaceを生成する
        引数 bird：ビームを放つこうかとん
        """
        super().__init__()
        self.vx, self.vy = bird.dire
        angle = math.degrees(math.atan2(-self.vy, self.vx))
        self.image = pg.transform.rotozoom(pg.image.load(f"fig/beam.png"), angle, 2.0)
        self.vx = math.cos(math.radians(angle))
        self.vy = -math.sin(math.radians(angle))
        self.rect = self.image.get_rect()
        self.rect.centery = bird.rect.centery+bird.rect.height*self.vy
        self.rect.centerx = bird.rect.centerx+bird.rect.width*self.vx
        self.speed = 10
        self.attack = 20

    def update(self):
        """
        ビームを速度ベクトルself.vx, self.vyに基づき移動させる
        引数 screen：画面Surface
        """
        self.rect.move_ip(self.speed*self.vx, self.speed*self.vy)
        if check_bound(self.rect) != (True, True):
            self.kill()


class Explosion(pg.sprite.Sprite):
    """
    爆発に関するクラス
    """
    def __init__(self, obj: "Bomb|Enemy", life: int):
        """
        爆弾が爆発するエフェクトを生成する
        引数1 obj：爆発するBombまたは敵機インスタンス
        引数2 life：爆発時間
        """
        super().__init__()
        img = pg.image.load(f"fig/explosion.gif")
        self.imgs = [img, pg.transform.flip(img, 1, 1)]
        self.image = self.imgs[0]
        self.rect = self.image.get_rect(center=obj.rect.center)
        self.life = life

    def update(self):
        """
        爆発時間を1減算した爆発経過時間_lifeに応じて爆発画像を切り替えることで
        爆発エフェクトを表現する
        """
        self.life -= 1
        self.image = self.imgs[self.life//10%2]
        if self.life < 0:
            self.kill()


class Enemy(pg.sprite.Sprite):
    """
    敵機に関するクラス
    """
    imgs = [pg.image.load(f"fig/alien{i}.png") for i in range(1, 4)]
    
    def __init__(self, boss):
        super().__init__()
        self.image = random.choice(__class__.imgs)
        self.rect = self.image.get_rect()
        self.vy = +6
        self.bound = random.randint(50, HEIGHT//2)  # 停止位置
        self.state = "down"  # 降下状態or停止状態
        self.interval = random.randint(50, 300)  # 爆弾投下インターバル
        if boss == "normal":
            self.rect.center = random.randint(0, WIDTH), 0
        if boss == "up": #ボスが登場したとき、ボス周辺に敵機が配置しないように設定
            self.interval = 40
            self.cen = random.randint(0, 1)
            if self.cen == 0:
                self.rect.center = random.randint(0, 400), 0
            else:
                self.rect.center = random.randint(1200, WIDTH), 0

    def update(self):
        """
        敵機を速度ベクトルself.vyに基づき移動（降下）させる
        ランダムに決めた停止位置_boundまで降下したら，_stateを停止状態に変更する
        引数 screen：画面Surface
        """
        if self.rect.centery > self.bound:
            self.vy = 0
            self.state = "stop"
        self.rect.centery += self.vy


class Gravity(pg.sprite.Sprite):
    """
    重力場に関するクラス
    """
    
    def __init__(self, life):
        super().__init__()
        self.life = life
        self.image = pg.Surface((WIDTH, HEIGHT))
        self.rect = self.image.get_rect()
        self.rect.center = (WIDTH/2, HEIGHT/2)
        pg.draw.rect(self.image, (128, 128, 128), (0, 0, WIDTH, HEIGHT))
        self.image.set_alpha(128)

    def update(self):
        self.life -= 1
        if self.life < 0:
            self.kill()
        

class Score:
    """
    打ち落とした爆弾，敵機の数をスコアとして表示するクラス
    爆弾：1点
    敵機：10点
    """
    def __init__(self):
        self.font = pg.font.Font(None, 50)
        self.color = (0, 0, 255)
        self.value = 790
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        self.rect = self.image.get_rect()
        self.rect.center = 100, HEIGHT-50

    def update(self, screen: pg.Surface):
        self.image = self.font.render(f"Score: {self.value}", 0, self.color)
        screen.blit(self.image, self.rect)


class Failure:
    """
    ゲームが失敗したときに表示する文のクラス
    """
    def __init__(self, screen):
        self.fonto = pg.font.Font(None, 150)
        self.txt = self.fonto.render("Game Over", True, (255, 255, 255))
        screen.blit(self.txt, [WIDTH/2-255, HEIGHT/2])
        self.fonto = pg.font.Font(None, 150)
        self.txt = self.fonto.render("Game Over", True, (0, 0, 0))
        screen.blit(self.txt, [WIDTH/2-260, HEIGHT/2])


class Success:
    """
    ゲームが成功したときに表示する文のクラス
    """
    def __init__(self, screen):
        self.fonto = pg.font.Font(None, 150)
        self.txt = self.fonto.render("Game Clear!", True, (255, 255, 255))
        screen.blit(self.txt, [WIDTH/2-305, HEIGHT/2])
        self.fonto = pg.font.Font(None, 150)
        self.txt = self.fonto.render("Game Clear!", True, (255, 215, 0))
        screen.blit(self.txt, [WIDTH/2-310, HEIGHT/2])


class Emp(pg.sprite.Sprite):
    """
    電磁パルスに関するクラス
    """
    def __init__(self, emys: "Enemy", bombs: Bomb, screen:pg.Surface):
        super().__init__()
        self.image = pg.Surface((WIDTH, HEIGHT))
        self.rect = self.image.get_rect()
        pg.draw.rect(self.image, (255, 255, 0), (0, 0, WIDTH, HEIGHT))
        self.image.set_alpha(128)
        screen.blit(self.image, [0, 0])
        self.state = "normal"
        for emy in emys:
            emy.interval = math.inf
            emy.image = pg.transform.laplacian(emy.image)
        for bomb in bombs:
            bomb.speed = 3
            bomb.state = "inactive"
        pg.display.update()
        time.sleep(0.05)
        

class Stage3(pg.sprite.Sprite):
    """
    3面に関するクラス
    """
    def __init__(self, screen: pg.Surface):
        """
        ３面ステージsurfaceを生成
        引数 screen：画面Surface
        """
        super().__init__()
        self.image = pg.image.load("fig/space.jpeg")
        pg.display.update()
        screen.blit(self.image, [0,0])


class Lastboss(pg.sprite.Sprite):
    """
    ラスボスに関するクラス
    """
    def __init__(self, screen: pg.Surface):
        """
        ラスボスsurfaceを生成
        引数 screen:画面Surface
        """
        super().__init__()
        self.image = pg.image.load("fig/lastboss2.png")
        self.rect = self.image.get_rect()
        self.rect.center = WIDTH//2, HEIGHT//2-50
        screen.blit(self.image, [WIDTH//2-200, HEIGHT//2-200])
        
        
def main():
    pg.display.set_caption("真！こうかとん無双")
    screen = pg.display.set_mode((WIDTH, HEIGHT))
    bg_img = pg.image.load(f"fig/pg_bg.jpg")
    score = Score()
    state = "normal"
    labo_life = 25  # ボスの体力を設定

    bird = Bird(3, (900, 400))
    bombs = pg.sprite.Group()
    beams = pg.sprite.Group()
    exps = pg.sprite.Group()
    emys = pg.sprite.Group()
    emp = pg.sprite.Group()
    gvts = pg.sprite.Group()
    sta3 = pg.sprite.Group()

    tmr = 0
    clock = pg.time.Clock()
    while True:
        key_lst = pg.key.get_pressed()
        for event in pg.event.get():
            if event.type == pg.QUIT:
                return 0
            if event.type == pg.KEYDOWN and event.key == pg.K_SPACE:
                beams.add(Beam(bird))
            if score.value >= 50 and key_lst[pg.K_RSHIFT]:
                if state != "stage3":  # 3面到達時に使用不可になるように設定
                    bird.state = "hyper"
                    bird.hyper_life = 500
                    score.value -= 50
            if event.type == pg.KEYDOWN and event.key == pg.K_e:
                if state != "stage3":  # 3面到達時に使用不可になるように設定
                    if score.value > 10:
                        emp.add(Emp(emys, bombs, screen)) 
                        score.value -= 10
            if event.type == pg.KEYDOWN and event.key == pg.K_RETURN and score.value > 100:
                if state != "stage3":  # 3面到達時に使用不可になるように設定
                    gvts.add(Gravity(400))
                    score.value -= 100
        if score.value >= 500:  # スコアが500以上で3面に突入
            state = "stage3"
        if state == "normal":
            screen.blit(bg_img, [0, 0])
        if state == "stage3":
            sta3.add(Stage3(screen))
            score.color = (255, 0, 0)
            if score.value >= 800 and labo_life > 0:  # スコアが800以上とボスの体力が０以下でなければ、敵機の爆弾投下インターバルの減少とボス出現
                state = "boss"
                labo = Lastboss(screen)

        if state == "boss":  # ボス出現時のみ敵機の出現率を上昇させる
            if tmr%100 == 0:  # 100フレームに一回、敵機出現
                emys.add(Enemy("up"))
        if state == "normal" or "stage3":
            if tmr%200 == 0:  # 200フレームに1回，敵機を出現させる
                emys.add(Enemy("normal"))

        for emy in emys:
            if emy.state == "stop" and tmr%emy.interval == 0:
                # 敵機が停止状態に入ったら，intervalに応じて爆弾投下
                bombs.add(Bomb(emy, bird))

        if state == "boss" and tmr%emy.interval == 0 and score.value >= 800:
            # ボスの爆弾投下設定
            bombs.add(Bomb(labo, bird))

        for emy in pg.sprite.groupcollide(emys, beams, True, True).keys():
            exps.add(Explosion(emy, 100))  # 爆発エフェクト
            score.value += 20  # 20点アップ
            bird.change_img(6, screen)  # こうかとん喜びエフェクト

        for bomb in pg.sprite.groupcollide(bombs, beams, True, True).keys():
            exps.add(Explosion(bomb, 50))  # 爆発エフェクト
            score.value += 5  # 5点アップ
        
        for bomb in pg.sprite.groupcollide(bombs, gvts, True, False).keys():
            bird.change_img(8, screen)
            exps.add(Explosion(bomb, 50))
            pg.display.update()

        for bomb in pg.sprite.spritecollide(bird, bombs, True):
            if bird.state == "hyper":
                exps.add(Explosion(bomb, 50))
                score.value += 1
            if bomb.state == "inactive":
                continue
            if bird.state == "normal":  
                bird.change_img(8, screen) # こうかとん悲しみエフェクト
                score.update(screen)
                Failure(screen)
                pg.display.update()
                time.sleep(2)
                return
        
        if state == "boss":
            for beam in pg.sprite.spritecollide(labo, beams, True):
                exps.add(Explosion(labo, 50))  # 爆発エフェクト
                bird.change_img(6, screen)  # こうかとん喜びエフェクト
                labo_life -= beam.attack  # ボスの体力減少設定
                print(labo_life)
                pg.display.update()

        bird.update(key_lst, screen)
        beams.update()
        beams.draw(screen)
        emys.update()
        emys.draw(screen)
        bombs.update()
        bombs.draw(screen)
        exps.update()
        exps.draw(screen)
        gvts.draw(screen)
        gvts.update()
        score.update(screen)
        pg.display.update()
        tmr += 1
        clock.tick(50)


if __name__ == "__main__":
    pg.init()
    main()
    pg.quit()
    sys.exit()
