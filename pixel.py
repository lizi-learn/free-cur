"""Small-grid character animation and fixed-hotspot functional pixel symbols."""
from pathlib import Path
from PIL import Image, ImageDraw
from cursor_style import pointer

ROOT=Path(__file__).resolve().parent
FRAME_MS=200
MOODS={
 'blink':[0,0,0,0,1,1,0,0], 'wink':[0,0,2,2,2,0,1,0],
 'hop':[0,0,3,3,3,0,0,0], 'think':[0,4,4,4,4,0,0,0],
 'shy':[0,5,5,5,5,0,1,0], 'sleep':[6,6,6,6,1,6,6,6],
 'wave':[0,2,7,7,2,7,0,0], 'happy':[0,1,2,3,7,3,2,0],
}
MOOD_POSTERS={'blink':1,'wink':2,'hop':3,'think':4,'shy':5,'sleep':6,'wave':7,'happy':3}
TASK_ROLES={'Hand','Wait','No','IBeam','SizeWE','SizeNS','SizeNWSE','SizeNESW','Help','NWPen','SizeAll','AppStarting'}
TASK_SEQUENCES={role:[0,1,2,3,3,2,1,0] for role in TASK_ROLES}
TASK_SEQUENCES.update(Hand=[0,0,1,1,2,2,3,0],Wait=[0,0,1,1,2,2,3,3],No=[0,1,0,3,0,1,0,3],IBeam=[0,0,1,2,2,3,2,0])
DURATIONS={'Arrow':300,'Help':250,'AppStarting':150,'Wait':350,'Crosshair':300,'IBeam':300,'NWPen':150,'No':200,
 'SizeNS':200,'SizeWE':200,'SizeNWSE':200,'SizeNESW':200,'SizeAll':200,'UpArrow':250,'Hand':200}
POSES={
 'Arrow':[0,0,0,0,1,1,0,0],
 'Help':[0,4,4,4,0,1,0,0],
 'AppStarting':[0,2,2,3,3,2,0,0],
 'Wait':[6,6,6,6,6,1,6,6],
 'Crosshair':[4,4,4,4,0,0,4,4],
 'IBeam':[0,0,0,0,0,1,0,0],
 'NWPen':[4,4,0,4,4,0,4,0],
 'No':[5,5,5,5,1,5,5,5],
 'SizeNS':[0,0,3,3,0,0,1,0],
 'SizeWE':[0,4,4,0,5,5,0,0],
 'SizeNWSE':[0,2,3,3,2,0,4,0],
 'SizeNESW':[4,0,2,3,3,2,0,0],
 'SizeAll':[4,4,0,2,2,0,5,0],
 'UpArrow':[0,0,2,2,3,3,2,0],
 'Hand':[0,2,2,7,7,2,0,0],
}
# Character-only movement encodes the task; the functional symbol and hotspot never move.
MOTION={
 'Arrow':[(0,0)]*8, 'Help':[(0,0),(1,0),(1,0),(0,0),(-1,0),(-1,0),(0,0),(0,0)],
 'AppStarting':[(0,0),(0,-1),(0,-2),(0,-2),(0,-1),(0,0),(0,0),(0,0)],
 'Wait':[(0,0)]*8, 'Crosshair':[(0,0)]*8, 'IBeam':[(0,0)]*8,
 'NWPen':[(0,0),(1,0),(0,0),(-1,0),(0,0),(1,0),(0,0),(-1,0)],
 'No':[(-2,0),(2,0),(-2,0),(2,0),(0,0),(0,0),(0,0),(0,0)],
 'SizeNS':[(0,0),(0,-1),(0,-2),(0,-1),(0,0),(0,1),(0,2),(0,1)],
 'SizeWE':[(0,0),(-1,0),(-2,0),(-1,0),(0,0),(1,0),(2,0),(1,0)],
 'SizeNWSE':[(0,0),(-1,-1),(-2,-2),(-1,-1),(0,0),(1,1),(2,2),(1,1)],
 'SizeNESW':[(0,0),(1,-1),(2,-2),(1,-1),(0,0),(-1,1),(-2,2),(-1,1)],
 'SizeAll':[(-2,0),(-1,-1),(0,-2),(1,-1),(2,0),(1,1),(0,2),(-1,1)],
 'UpArrow':[(0,1),(0,1),(0,0),(0,0),(0,-1),(0,-2),(0,-1),(0,0)],
 'Hand':[(0,0),(0,0),(0,-1),(0,-1),(0,0),(0,0),(0,0),(0,0)],
}
BEHAVIORS={
 'Arrow':dict(action='日常陪伴 · 轻轻眨眼',meaning='普通选择；小角色站稳，不用大动作分散注意力。',example='空白区域、普通内容'),
 'Help':dict(action='歪头思考 · 小问号',meaning='对象提供帮助说明；用好奇的歪头表达“这是什么”。',example='系统帮助选择状态'),
 'AppStarting':dict(action='打起精神 · 三点进度',meaning='后台仍在处理，但你可以继续操作；和完全等待区分。',example='应用后台加载'),
 'Wait':dict(action='抱枕等候 · 沙漏落沙',meaning='当前需要等待；动作放慢，沙漏提示还在处理，不用重复点击。',example='忙碌、阻塞操作'),
 'Crosshair':dict(action='专注瞄准 · 十字准星',meaning='精确选点；准星中心固定，角色不位移，避免遮挡目标。',example='绘图、截图、精确定位'),
 'IBeam':dict(action='安静阅读 · 偶尔眨眼',meaning='可以输入或选择文字；保持安静，只让细小表情变化。',example='输入框、可选文本'),
 'NWPen':dict(action='认真书写 · 铅笔笔迹',meaning='手写或绘制；用小笔和短短的像素笔迹表达书写。',example='手写笔、画布'),
 'No':dict(action='摇头拒绝 · 禁止标记',meaning='此处不允许操作或放下对象；摇头和红色叉号明确拒绝。',example='禁用目标、不可放置区域'),
 'SizeNS':dict(action='上下发力 · 纵向调整',meaning='只改变高度；角色沿上下方向轻轻发力，双箭头保持固定。',example='窗口上边缘、下边缘'),
 'SizeWE':dict(action='左右发力 · 横向调整',meaning='只改变宽度；角色左右倾身，区别于纵向调整。',example='窗口左边缘、右边缘'),
 'SizeNWSE':dict(action='斜向伸展 · 左上 ↔ 右下',meaning='沿左上到右下调整；动作方向与窗口角落一致。',example='窗口左上角、右下角'),
 'SizeNESW':dict(action='反斜伸展 · 左下 ↔ 右上',meaning='沿左下到右上调整；与另一条对角线使用相反动作。',example='窗口左下角、右上角'),
 'SizeAll':dict(action='四向搬运 · 跟着用力',meaning='移动整个对象，不改变尺寸；角色在四个方向依次发力。',example='可拖动标题栏、对象'),
 'UpArrow':dict(action='抬头举手 · 候选选择',meaning='向上选择或系统候选状态；动作向上，避免混同普通箭头。',example='系统候选选择'),
 'Hand':dict(action='wink 挥手 · 可以点我',meaning='这里可点击；用挥手和小爱心邀请操作，热点保持在指尖。',example='链接、可点击按钮'),
}
BEHAVIORS['Hand'].update(action='伸手点选 · 邀请点击',meaning='角色伸出食指并做轻点动作；清楚提示这里可以点，不用通用挥手代替。')
BEHAVIORS['Wait'].update(action='捧着沙漏 · 耐心等待',meaning='角色醒着看沙漏，细微呼吸与落沙提示处理中；不再用抱枕睡觉表达忙碌。')
BEHAVIORS['No'].update(action='双掌示停 · 摆头拒绝',meaning='双掌向前作“停止”姿势，轻轻摆头；不是害羞或邀请互动。')
BEHAVIORS['IBeam'].update(action='安静阅读 · 轻轻翻页',meaning='捧书阅读、偶尔眨眼和翻页；身体稳定，避免在输入或选字时分散注意力。')
BEHAVIORS['Help'].update(action='举起放大镜 · 好奇查看',meaning='通过放大镜仔细观察，表达寻求说明；与精确选点的准星区分。')
BEHAVIORS['NWPen'].update(action='拿笔书写 · 笔尖起落',meaning='角色真正拿着笔在小本子上写字，与阅读文字的翻页动作区分。')
BEHAVIORS['SizeAll'].update(action='搬动箱子 · 整体移动',meaning='双手搬动完整箱子，表达移动对象；区别于拉伸双箭头改变尺寸。')
BEHAVIORS['AppStarting'].update(action='调试齿轮 · 后台工作',meaning='角色拿工具调整齿轮，表示后台仍在工作但可继续操作；不同于看沙漏等待。')
for role in ('SizeNS','SizeWE','SizeNWSE','SizeNESW'):
    BEHAVIORS[role]['meaning']+=' 角色实际握住并伸展对应方向的双箭头，身体不再整张平移。'
for role in TASK_ROLES:MOTION[role]=[(0,0)]*8
HOTSPOTS={'Arrow':(1,1),'Help':(1,1),'AppStarting':(1,1),'Wait':(8,8),
 'Crosshair':(8,8),'IBeam':(6,10),'NWPen':(2,17),'No':(8,8),
 'SizeNS':(8,8),'SizeWE':(8,8),'SizeNWSE':(8,8),'SizeNESW':(8,8),
 'SizeAll':(8,8),'UpArrow':(8,1),'Hand':(6,1)}
_frames={}
_task_frames={}


def enabled(item):
    return all((ROOT/f'artwork/pixel-{item["id"]}/pose-{i}.png').exists() for i in range(8))


def advanced(item):
    return item['id']=='diana'


def behaviors(item):
    if advanced(item):return BEHAVIORS
    actions={'Arrow':'日常眨眼','Help':'歪头思考','AppStarting':'打起精神','Wait':'沙漏等候',
        'Crosshair':'专注思考','IBeam':'安静眨眼','NWPen':'思考与小笔标记','No':'双掌示停',
        'SizeNS':'抬手伸展 · 纵向标记','SizeWE':'思考伸展 · 横向标记','SizeNWSE':'小小伸展 · 斜向标记',
        'SizeNESW':'小小伸展 · 反斜标记','SizeAll':'挥手引导 · 移动标记','UpArrow':'抬手向上','Hand':'伸手点选'}
    return {role:dict(action=actions[role],meaning='8 姿势基础像素版：以角色表情与固定功能标记区分用途；尚未逐功能绘制专用道具关键帧。',example=value['example']) for role,value in BEHAVIORS.items()}


def pose(index,item=None):
    global _frames
    ident=(item or {}).get('id','diana')
    if ident not in _frames:
        _frames[ident]=[Image.open(ROOT/f'artwork/pixel-{ident}/pose-{i}.png').convert('RGBA') for i in range(8)]
    return _frames[ident][index].copy()


def task_pose(role,frame):
    if role not in _task_frames:
        _task_frames[role]=[Image.open(ROOT/f'artwork/pixel-diana-v2/{role}/{i}.png').convert('RGBA') for i in range(4)]
    return _task_frames[role][TASK_SEQUENCES[role][frame%8]].copy()


def character_layer(role,frame,item=None):
    image=Image.new('RGBA',(64,64))
    if (item or {}).get('id','diana')=='diana' and role in TASK_ROLES:
        image.alpha_composite(task_pose(role,frame).resize((52,52),Image.Resampling.NEAREST),(10,10))
        return image
    dx,dy=MOTION[role][frame%8]
    image.alpha_composite(pose(POSES[role][frame%8],item).resize((52,52),Image.Resampling.NEAREST),(10+dx,10+dy))
    return image


def render(item,role,size,frame):
    image=character_layer(role,frame,item)
    d=ImageDraw.Draw(image)
    ink='#403346';white='#fff8ef';pink=item.get('color','#ee8d9a')
    def line(points,fill=pink,width=2):
        d.line(points,fill=ink,width=width+2)
        d.line(points,fill=fill,width=width)
    def shape(points):
        d.polygon(points,fill=pink)
        d.line(points+[points[0]],fill=ink,width=1)
    if role in ('Arrow','Help','AppStarting'):
        pointer(image,pink,origin=(1,1),pixel=True)
        if role=='Help':
            d.rectangle((12,1,21,11),fill=pink,outline=ink)
            d.line((15,3,18,3,18,5,16,7),fill=white,width=1);d.point((16,9),fill=white)
        if role=='AppStarting':
            for i in range(3):d.rectangle((15+i*4,4,17+i*4,6),fill=pink if frame%3==i else '#d6bac8')
    elif role=='Hand':
        shape([(6,1),(9,1),(9,8),(11,6),(14,7),(16,10),(15,19),(8,20),(2,13),(3,10),(6,12)])
    elif role=='Wait':
        # A pixel hourglass remains fixed while the character changes expression.
        line([(2,2),(14,2)]);line([(2,15),(14,15)])
        d.polygon([(4,4),(12,4),(8,8),(12,13),(4,13),(8,8)],fill=white,outline=ink)
        level=frame%4
        d.line((5+level,5,11-level,5),fill=pink,width=1)
        d.line((8,7,8,10),fill=pink,width=1)
        d.line((7-level,12,9+level,12),fill=pink,width=1)
    elif role=='IBeam':
        line([(2,1),(10,1)]);line([(6,1),(6,19)]);line([(2,19),(10,19)])
    elif role=='Crosshair':
        line([(8,1),(8,15)]);line([(1,8),(15,8)])
        if frame in (0,1,4,5):
            for x,y in ((2,2),(13,2),(2,13),(13,13)):d.rectangle((x,y,x+1,y+1),fill=pink)
    elif role=='NWPen':
        shape([(2,17),(4,11),(13,2),(17,6),(7,15)])
        d.line((2,21,3+frame%4*2,21),fill=pink,width=1)
    elif role=='No':
        d.polygon([(4,1),(12,1),(15,4),(15,12),(12,15),(4,15),(1,12),(1,4)],fill='#de637e',outline=ink)
        d.line((5,5,11,11),fill=white,width=2);d.line((11,5,5,11),fill=white,width=2)
    elif role=='UpArrow':
        shape([(8,1),(1,8),(5,8),(5,18),(11,18),(11,8),(15,8)])
    else:
        points={'SizeNS':[(8,1),(8,15)],'SizeWE':[(1,8),(15,8)],
         'SizeNWSE':[(2,2),(14,14)],'SizeNESW':[(2,14),(14,2)],
         'SizeAll':[(8,1),(8,15),(1,8),(15,8)]}[role]
        for a,b in zip(points[::2],points[1::2]):
            line([a,b])
            dx=(b[0]>a[0])-(b[0]<a[0]);dy=(b[1]>a[1])-(b[1]<a[1])
            for tip,sign in ((a,1),(b,-1)):
                x,y=tip;ux=dx*sign;uy=dy*sign
                line([(x+ux*4-uy*3,y+uy*4+ux*3),tip,(x+ux*4+uy*3,y+uy*4-ux*3)],width=1)
    hot=tuple(round(n*size/64) for n in HOTSPOTS[role])
    return image.resize((size,size),Image.Resampling.NEAREST),hot
