import tkinter as tk
import PIL
from PIL import Image, ImageTk
import sys, threading, time, cv2, os
import PySimpleGUI as sg
import numpy as np
import datetime
"""
The code originally developed by SondreKindem, 
https://github.com/SondreKindem/PySimpleGUI-video-player-with-OpenCV/blob/master/VideoPlayer.py

Modified by jiwon yeon
"""

class App:
    """
    TODO: need to accomodate changing speed: maybe achievable by changing self.delay
    TODO: maybe want to include an error message section? 
    TODO: if the GoToFrame's frame exceeds the video's frames, give an error message
    """
    
    def __init__(self):

        # ------ App states ------ #
        self.play = False  # Is the video currently playing?
        self.delay = 0.023  # Delay between frames - not sure what it should be, not accurate playback
        self.frame = 0  # Current frame
        self.frames = None  # Number of frames
        self.speed = 2
        # ------ Other vars ------ #
        self.vid = None
        self.photo = None
        self.next = "1"
        # ------ Menu Definition ------ #      
        sg.theme('default1')
        filebrowser = [
            sg.Input(default_text="Open a video file", size=(50,1), enable_events="True", font=10, key='videopath',
                background_color="white", border_width=1, expand_x="True", text_color="black"), 
            sg.Button('Open', key='-VideoOpen-', size=(10,1), pad=(0,2), font=('11')), 
            sg.Button('Exit', key='-ClosePlayer-', size=(10,1), pad=(2,2),font=('11'))]
        
        speed_list = np.arange(.5, 4.05, .5)    
        speed_list = ["%.2f" % x for x in speed_list]
        videocontroller = sg.Frame('Video Controller', 
            [[sg.Text('Playback speed', font=('8'), text_color="black")],
            [sg.Text('x', pad=((1,0),2), size=(1,1), font=('5'),justification='right', text_color="black"),
             sg.Spin(speed_list, initial_value='1.00', enable_events="True", size=(3,2), font=('15'), 
                     key='vidspeed_spin', pad=((0,3),(2,0)), tooltip="Playback speed", text_color="black", background_color="white"),
             sg.Slider((0.5, 4), default_value=1, resolution=0.5, orientation='h', disable_number_display="True",
                       key='vidspeed_slider', enable_events="True", size=(15,15), tooltip='Playback speed',pad=(2,0))],
            [sg.Text('Go to frame', font=('8'), text_color="black"),
             sg.Input(key='-whichFrame-', size=(5,3), background_color='white', text_color="black",
                      font=('8'), focus=True), 
             sg.Button('Go', key='-GoToFrame-', size=(4,1), font=('8'))]
            ],
            font=("Arial Bold", 13), title_color="black", size=(200,100),pad=((30,0),(0,0)))

        eyedatacontroller = sg.Frame('Eyedata Controller', [
            [sg.Text('Overlay gaze', font=('8'), text_color="black")],
            [sg.Input(default_text="Open an eye data", size=(20,1), enable_events="True", font=10, 
                      key='-EyeDataDir-', background_color="white", text_color="black")],
            [sg.Button('Open', key='-OpenEyeData-', size=(5,1), font=('8')), 
             sg.Button('Close', key='-CloseEyeData-', size=(5,1), font=('8'))]
             ],
            font=("Arial Bold", 13), title_color="black", size=(200,100))

        videostatus = [sg.Slider(range=(0,100), default_value=0, resolution=1, orientation='h', pad=(5,2), 
                                key='vid_slider', expand_x="True", tooltip="#Frame", enable_events="True", 
                                text_color="black",font=('Arial','15')), 
                       sg.Text('0:00:00/0:00:00', key='counter', font=('Arial', '15'), pad=(2,2), tooltip="Time", 
                               text_color="black", justification='bottom'),
                        ]
          
        controllers = [sg.Column([[sg.Button('', tooltip='Play',image_filename='play.png', image_subsample=6, key='play'),
                                      sg.Button('', tooltip='Pause',image_filename='pause.png', image_subsample=6, key='pause')]],        
                                    justification='center'),
                            sg.Column([[sg.Button('', tooltip='Ten frames backward',image_filename='multiFB.png', image_subsample=6, key='tenframe_backward', pad=((20,2),(2,2))),
                                        sg.Button('', tooltip='One frame backward', image_filename='oneFB.png', image_subsample=6,pad=(2,2), key='oneframe_backward'),
                                        sg.Button('', tooltip='One frame forward', image_filename='oneFF.png', image_subsample=6, pad=(2,2), key='oneframe_forward'),
                                        sg.Button('', tooltip='Ten frames forward', image_filename='multiFF.png', image_subsample=6, pad=(2,2), key='tenframe_forward')]], 
                                        justification='center'),
                            sg.Column([[videocontroller, eyedatacontroller]], justification='right')]         

        layout = [[
            filebrowser,                   
            [sg.Canvas(size=(800,500), key="canvas", background_color="black", expand_x="t", expand_y="t")],
            videostatus,
            controllers
                  ]]

        self.window = sg.Window('Player', layout, location=(250,250), resizable='t').Finalize()
        
        # Get the tkinter canvas for displaying the video
        canvas = self.window.Element("canvas")
        self.canvas = canvas.TKCanvas

        # Start video display thread
        self.load_video()
        
        while True:  # Main event Loop
            event, values = self.window.Read()

            # read canvas size
            width = self.canvas.winfo_width()
            height = self.canvas.winfo_height()
            
            if event == sg.WIN_CLOSED or event == '-ClosePlayer-':
                """Handle exit"""
                break

            if event == '-VideoOpen-':
                """when the file is input"""
                video_path = None
                try: 
                    video_path = sg.filedialog.askopenfile(initialdir=os.getcwd).name                     
                except AttributeError:
                    print("no video selected, doing nothing")

                if video_path:
                    # Initialize video                    
                    self.vid = MyVideoCapture(video_path)

                    # Change size of the video
                    self.vid_width = width
                    self.vid_height = height                                       
                    self.frames = int(self.vid.frames)
                    self.fps = self.vid.fps                    

                    # Update slider to match amount of frames
                    self.window.Element("vid_slider").Update(range=(0, int(self.frames)), value=0)
                    # Update right side of counter                    
                    self.window.Element("counter").Update("0:00:00/"+self.vid.video_time)
                    
                    # Reset frame count            
                    self.delay = 1 / self.fps

                    # Get current playback speed
                    self.speed = float(values['vidspeed_spin'])

                    # Update the video path text field
                    self.window.Element("videopath").Update(video_path)

            if event == 'play':
                self.play = True
                    
            if event == 'pause':
                self.play = False

            if event == 'oneframe_forward':
                self.play = False
                self.set_frame(self.frame+1)

            if event == 'tenframe_forward':
                self.set_frame(self.frame+10)
            
            if event == 'oneframe_backward':
                self.play = False
                self.set_frame(self.frame-1)

            if event == 'tenframe_backward':
                self.set_frame(self.frame-10)

            if event == 'vid_slider':
                self.set_frame(int(values["vid_slider"]))

            if event == '-GoToFrame-':                
                frame_to_move = values["-whichFrame-"]
                if frame_to_move.isdigit():
                    self.set_frame(int(frame_to_move))
                else:
                    pass        ####### want to make an error message

            if event == '':
                pass

            if event == 'vidspeed_spin':
                self.speed = float(values['vidspeed_spin'])
                self.window.Element('vidspeed_slider').Update(self.speed)
                # self.wait = self.fps*float(self.speed)
            
            if event == 'vidspeed_slider':
                self.speed = values['vidspeed_slider']
                self.window.Element('vidspeed_spin').Update(self.speed)
                # self.wait = self.fps*self.speed
 
        # Exiting
        print("bye :)")
        sys.exit()
        # self.window.close()

    #################
    # Video methods #
    #################
    def load_video(self):
        """Start video display in a new thread"""
        thread = threading.Thread(target=self.update, daemon="True", args=()).start()        

    def update(self):
        """Update the canvas element with the next video frame recursively"""
        start_time = time.time()        
        if self.vid:     
            if self.play:
                # Get a frame from the video source only if the video is supposed to play
                ret, frame = self.vid.get_frame()

                if ret:
                    self.photo = PIL.ImageTk.PhotoImage(
                        image=PIL.Image.fromarray(frame).resize((self.vid_width, self.vid_height), Image.NEAREST)
                    )
                    self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)

                    self.frame += 1
                    self.update_counter(self.frame)

            # Uncomment these to be able to manually count fps
            # print(str(self.next) + " It's " + str(time.ctime()))
            # self.next = int(self.next) + 1
        # The tkinter .after method lets us recurse after a delay without reaching recursion limit. We need to wait
        # between each frame to achieve proper fps, but also count the time it took to generate the previous frame.
        self.canvas.after(abs(int((self.delay - (time.time() - start_time)) * 1000)), self.update)

    def set_frame(self, frame_no):
        """Jump to a specific frame"""
        if self.vid:
            # Get a frame from the video source only if the video is supposed to play
            ret, frame = self.vid.goto_frame(frame_no)
            self.frame = frame_no
            self.update_counter(self.frame)

            if ret:
                self.photo = PIL.ImageTk.PhotoImage(
                    image=PIL.Image.fromarray(frame).resize((self.vid_width, self.vid_height), Image.NEAREST))
                self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)

    def update_counter(self, frame):
        """Helper function for updating slider and frame counter elements"""        
        self.window.Element("vid_slider").Update(value=frame)
        seconds = round(frame/self.vid.fps)
        current_time = str(datetime.timedelta(seconds=seconds))
        self.window.Element("counter").Update("{}/{}".format(current_time, self.vid.video_time))


class MyVideoCapture:
    """
    Defines a new video loader with openCV
    Original code from https://solarianprogrammer.com/2018/04/21/python-opencv-show-video-tkinter-window/
    Modified by SondreKindem
    """
    def __init__(self, video_source):
        # Open the video source
        self.vid = cv2.VideoCapture(video_source)
        if not self.vid.isOpened():
            raise ValueError("Unable to open video source", video_source)

        # Get video source width and height
        self.width = self.vid.get(cv2.CAP_PROP_FRAME_WIDTH)
        self.height = self.vid.get(cv2.CAP_PROP_FRAME_HEIGHT)
        self.frames = self.vid.get(cv2.CAP_PROP_FRAME_COUNT)
        self.fps = self.vid.get(cv2.CAP_PROP_FPS)
        seconds = round(self.frames / self.fps)
        self.video_time = str(datetime.timedelta(seconds=seconds))
        self.current_frame = 0
        self.frame_grabbed = [-1]

    def get_frame(self):
        """
        Return the next 10 frames
        """ 
        if self.vid.isOpened():
            ret, frame = self.vid.read()
            if ret:
                # Return a boolean success flag and the current frame converted to BGR
                return ret, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                return ret, None
        else:
            return 0, None   
        
    def goto_frame(self, frame_no):
        """
        Go to specific frame
        """
        if self.vid.isOpened():
            self.vid.set(cv2.CAP_PROP_POS_FRAMES, frame_no)  # Set current frame
            ret, frame = self.vid.read()  # Retrieve frame
            if ret:
                # Return a boolean success flag and the current frame converted to BGR
                return ret, cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            else:
                return ret, None
        else:
            return 0, None
        
    # Release the video source when the object is destroyed
    def __del__(self):
        if self.vid.isOpened():
            self.vid.release()


if __name__ == '__main__':
    App()
