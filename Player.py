
# -*- mode: python ; coding: utf-8 -*-

import tkinter as tk
import pygame
import os
import sys
import time
import shutil
import configparser
from datetime import datetime, timedelta
import threading
from tkinter import messagebox
from PIL import Image, ImageTk


def res(relative_path):
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class MusiclyricsPlayer:
    def __init__(self, root):
        self.root = root
        self.root.title("音乐歌词播放器")
        self.root.geometry("500x300")
        self.root.resizable(width=False, height=False)
        self.root.iconbitmap(res("musicboxicon.ico"))
        
        # 初始化配置
        self.config = configparser.ConfigParser()
        self.config.read(res("default.ini"), encoding="utf-8")
        self.song_path1 = res(self.config["DEFAULT"]["SongPath1"])
        self.song_name1 = self.config["DEFAULT"]["SongName1"]
        self.song_length1 = self.timestr_to_sec(self.config["DEFAULT"]["SongLength1"])
        self.song_path2 = res(self.config["DEFAULT"]["SongPath2"])
        self.song_name2 = self.config["DEFAULT"]["SongName2"]
        self.song_length2 = self.timestr_to_sec(self.config["DEFAULT"]["SongLength2"])
        
        self.tvs = tk.StringVar()
        
        # 音频系统初始化
        pygame.mixer.init()
        pygame.mixer.music.load(self.song_path1)
        self.start_sound = pygame.mixer.Sound(res("start.wav"))
        self.song = None
        self.is_playing = False
        self.current_time = 0
        self.lyrics1 = []
        self.lyrics1_index = 0
        self.volume = 100
        self.update_volume()
        self.played = False
        
        # 加载图片
        self.bg_img = tk.PhotoImage(file=res("bg.png"))
        self.bg_label = tk.Label(self.root, image=self.bg_img)
        self.img = Image.open(res("musicbox.png"))
        self.musicbox = ImageTk.PhotoImage(self.img)
        self.musicbox_label = tk.Label(self.root, image=self.musicbox)
        self.set_alpha(0)
        self.bg_label.place(x=0, y=0)
        
        # 构建UI
        self.setup_player()
        self.root.after(4000, self.setup_ui)
        
        # 键盘事件绑定
        self.root.bind("<Return>", self.toggle_play)
        self.root.bind("<BackSpace>", self.replay)
        self.root.bind("<Escape>", self.exit_app)
        self.root.bind("+", self.volume_add)
        self.root.bind("-", self.volume_rem)
        self.root.bind("q", self.exit_app)
        self.root.bind("Q", self.exit_app)
        
        # 加载歌词
        self.current_song = 1
        self.load_lyrics1()
        self.update_combined_display()
    
    def set_alpha(self, alpha_value):
        # 确保图片是RGBA模式
        if self.img.mode != 'RGBA':
            self.img = self.img.convert('RGBA')
        
        # 创建带透明度的新图片
        alpha_img = Image.new('L', self.img.size, alpha_value)
        self.img.putalpha(alpha_img)
        
        # 创建PhotoImage对象
        self.musicbox = ImageTk.PhotoImage(self.img)
        
        # 更新Label图片
        if hasattr(self, 'musicbox_label'):
            self.musicbox_label.config(image=self.musicbox)
    
    def update_background_size(self):
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        if window_width > 1 and window_height > 1:  # 确保窗口大小有效
            resized_image = self.original_image.resize(
                (window_width, window_height), Image.LANCZOS)
            self.bg_img = ImageTk.PhotoImage(resized_image)
            if not self.bg_label:
                self.bg_label = tk.Label(self.root, image=self.bg_img)
                self.bg_label.place(x=0, y=0)
            else:
                self.bg_label.config(image=self.bg_img)
    
    def resize_background(self, event):
        if hasattr(self, 'original_image'):
            self.update_background_size()
    
    def load_lyrics1(self):
        """加载第一首歌的歌词"""
        try:
            with open(res("lyrics1.dat"), "r", encoding="utf-8") as f:
                raw_lyrics1 = [line.strip() for line in f.readlines()]
                self.lyrics1 = self.parse_lyrics(raw_lyrics1)
        except FileNotFoundError:
            print("歌词文件未找到")
            self.lyrics1 = ["歌词文件错误"]
    
    def load_lyrics2(self):
        """加载第二首歌的歌词"""
        try:
            with open(res("lyrics2.dat"), "r", encoding="utf-8") as f:
                raw_lyrics2 = [line.strip() for line in f.readlines()]
                self.lyrics1 = self.parse_lyrics(raw_lyrics2)
        except FileNotFoundError:
            print("歌词文件未找到")
            self.lyrics1 = ["歌词文件错误"]
    
    def parse_lyrics(self, raw_lyrics):
        parsed = []
        for line in raw_lyrics:
            if line.startswith("["):
                time_end = line.find("]")
                time_str = line[1:time_end]
                lyric = line[time_end+1:].strip()
                parsed.append((self.timestr_to_sec(time_str), lyric))
        return parsed
    
    def timestr_to_sec(self, time_str):
        h, m, s = map(int, time_str.split(":"))
        return h * 3600 + m * 60 + s
    
    def volume_add(self, event=None):
        self.volume = min(100, self.volume + 5)
        self.update_volume()
        self.update_combined_display()
    
    def volume_rem(self, event=None):
        self.volume = max(0, self.volume - 5)
        self.update_volume()
        self.update_combined_display()
    
    def update_volume(self):
        pygame.mixer.music.set_volume(self.volume / 100.0)
    
    def set_volume(self, value):
        self.volume = max(0, min(100, int(value)))
        self.update_volume()
        self.update_volume_display()
        
    def play(self):
        if not self.played:
            pygame.mixer.music.play()
            self.is_playing = True
            self.played = True
            threading.Thread(target=self.update_playback, daemon=True).start()
        else:
            self.continue_()
    
    def pause(self):
        if self.is_playing and self.played:
            pygame.mixer.music.pause()
            self.is_playing = False
    
    def continue_(self):
        if not self.is_playing and self.played:
            pygame.mixer.music.unpause()
            self.is_playing = True
    
    def toggle_play(self, event=None):
        if not self.played:
            self.play()
        elif self.is_playing:
            self.pause()
        else:
            self.continue_()
    
    def stop(self):
        pygame.mixer.music.stop()
        self.is_playing = False
        self.played = False
        self.current_time = 0
        self.update_combined_display()
    
    def replay(self, event=None):
        self.stop()
        self.play()
    
    def update_playback(self):
        last_update = 0
        while True:
            if self.is_playing:
                current_time = pygame.mixer.music.get_pos() / 1000
                # 只有当时间变化超过0.1秒或歌词需要更新时才刷新
                if abs(current_time - last_update) > 0.1 or self.need_lyrics_update(current_time):
                    self.current_time = current_time
                    self.update_lyrics_display()
                    self.update_combined_display()
                    last_update = current_time
                pygame.time.delay(50)  # 减少延迟时间
    
    def need_lyrics_update(self, current_time):
        # 检查当前时间是否接近下一句歌词的时间点
        for i, (time, lyric) in enumerate(self.lyrics1):
            if time - 0.2 <= current_time <= time + 0.2:  # 前后0.2秒的缓冲区间
                return True
        return False
    
    def update_lyrics_display(self):
        current_sec = self.current_time
        for i, (time, lyric) in enumerate(self.lyrics1):
            if time <= current_sec < (self.lyrics1[i+1][0] if i < len(self.lyrics1)-1 else float('inf')):
                # 只有当歌词确实变化时才更新显示
                if self.current_lyrics_label['text'] != lyric:
                    self.current_lyrics_label.config(text=lyric)
                    if i < len(self.lyrics1) - 1:
                        self.next_lyrics_label.config(text=self.lyrics1[i+1][1])
                    else:
                        self.next_lyrics_label.config(text="")
                break
    
    def update_combined_display(self, *args):
        self.current_td = timedelta(seconds=int(self.current_time))
        if self.current_song == 1:
            self.total_td = timedelta(seconds=self.song_length1)
        else:
            self.total_td = timedelta(seconds=self.song_length2)
        
        self.tvs.set(f"已播放：{str(self.current_td)}/{str(self.total_td)}      音量: {self.volume}%")
    
    def upgrade_song(self, song_arg, *args):
        self.stop()
        if song_arg == 1:
            pygame.mixer.music.load(self.song_path1)
            self.title_label.config(text=self.song_name1)
            self.current_song = 1
            self.load_lyrics1()
        elif song_arg == 2:
            pygame.mixer.music.load(self.song_path2)
            self.title_label.config(text=self.song_name2)
            self.current_song = 2
            self.load_lyrics2()
        
        # 重置播放状态
        self.played = False
        self.is_playing = False
        self.current_time = 0
        self.update_combined_display()
        self.update_lyrics_display()
    
    def copy_videos(self, source_dir="videos"):
        desktop = os.path.join(os.path.expanduser('~'), 'Desktop')
        target_dir = os.path.join(desktop, 'Videos')
        os.makedirs(target_dir, exist_ok=True)
        
        def copy(filename):
            src_path = res(os.path.join(source_dir, filename))
            shutil.copy2(src_path, target_dir)
            print(f"已复制: {filename}")
        
        try:
            copy("最初的梦想.mp4")
            copy("梦开始的地方.mp4")
            messagebox.showinfo("成功", "资源释放成功：请于桌面查看")
        except PermissionError:
            messagebox.showerror("失败", "资源释放失败：权限不足，请以管理员身份运行")
        except Exception as e:
            messagebox.showerror("失败", f"资源释放错误：错误代码：{e}")
    
    def setup_player(self):
        # 播放启动音效
        self.start_sound.play()
        
        # 初始化图片
        self.set_alpha(0)  # 完全透明
        self.musicbox_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # 渐显动画
        def fade_in():
            current_alpha = 0
            def step():
                nonlocal current_alpha
                current_alpha += 5
                if current_alpha <= 255:
                    self.set_alpha(current_alpha)
                    self.root.after(25, step)  # 每25毫秒执行一次
            step()  # 开始动画
        
        # 渐隐动画
        def fade_out():
            current_alpha = 255
            def step():
                nonlocal current_alpha
                current_alpha -= 5
                if current_alpha >= 0:
                    self.set_alpha(current_alpha)
                    self.root.after(45, step)  # 每50毫秒执行一次
                else:
                    self.musicbox_label.place_forget()
            step()  # 开始动画
        
        fade_in()
        self.root.after(1500, fade_out)
    
    def setup_ui(self):
        # 背景设置
        self.bg_label.place(x=0, y=0)
        
        # 菜单栏
        self.menubar = tk.Menu(self.root)
        self.root.config(menu=self.menubar)
        
        # 子菜单
        song_menu = tk.Menu(self.menubar, tearoff=0)
        song_menu.add_command(label="梦开始的地方", command=lambda: self.upgrade_song(2))
        song_menu.add_command(label="最初的梦想", command=lambda: self.upgrade_song(1))
        self.menubar.add_cascade(label="歌曲", menu=song_menu)
        
        self.menubar.add_command(label="释放资源", command=self.copy_videos)
        self.menubar.add_command(label="退出(Q)", command=self.exit_app)
        
        # 歌曲标题
        self.title_label = tk.Label(self.root, text=self.song_name1, 
                                font=("宋体", 38, "bold"), fg="white", bg="#1e1e1e")
        self.title_label.pack(pady=10)
        
        # 歌词显示区域
        self.current_lyrics_label = tk.Label(self.root, text="...", 
                                        font=("宋体", 22, "bold"), fg="white", bg="#1e1e1e")
        self.next_lyrics_label = tk.Label(self.root, text="...", 
                                        font=("宋体", 22), fg="white", bg="#1e1e1e")
        
        # 时间音量显示
        self.time_label = tk.Label(self.root, textvariable=self.tvs,
                                font=("宋体", 12), fg="white", bg="#1e1e1e")
        
        # 键盘提示
        self.keyboard_tip = tk.Label(self.root, 
                                text="播放/暂停 Enter   重新播放 Backspace   退出 Esc   音量调节 +/-",
                                font=("宋体", 10), fg="white", bg="#1e1e1e")
    
        # 布局
        self.current_lyrics_label.pack(pady=20)
        self.next_lyrics_label.pack(pady=10)
        self.time_label.pack(side="bottom", fill="x", pady=5)
        self.keyboard_tip.pack(side="bottom", fill="x", pady=5)
    
    def exit_app(self, event=None):
        if messagebox.askyesno("退出", "确定要退出吗？"):
            self.is_playing = False  # 停止播放循环
            pygame.mixer.music.stop()
            pygame.mixer.quit()
            self.root.destroy()
            self.root.quit()
        else:
            return False
    
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    root = tk.Tk()
    app = MusiclyricsPlayer(root)
    app.run()