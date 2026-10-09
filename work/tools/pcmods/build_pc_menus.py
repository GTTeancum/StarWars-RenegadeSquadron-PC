r"""Builds the PC settings menus as file overrides (mods\files).

The game's own GUIMenu pages are extended the way the shipped pages are built:
widgets are copies of existing Asura widgets (same styles, same textures) bound
by name to console variables the host registers (PC.*, see
work\project\source\profiles\renegade\host\pc_settings.cpp) and to console
commands (PC_*). Added:

  Main menu            Quit Game button -> MP_PCQuit (Are You Sure? Yes/No)
  Options              Video Options button -> MP_VideoOptions_FrontEnd
  Controls             Gamepad Settings button -> MP_PCControls_FrontEnd
  In-game Options      Video Options -> MP_VideoOptions_InGame
  In-game Controls     Gamepad Settings -> MP_PCControls_InGame

Usage: python build_pc_menus.py [--game <data\PSP_GAME\USRDIR>] [--out <mods\files>]
"""
import argparse, copy, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import asura_gui as G
import asura_text as T
H = G.asura_hash
MENU_TEXT_PAGE = 0x0033155F

TEXTS = {
    'PC_VIDEO_OPTIONS': 'Video Options',
    'PC_RES_0': '1280 x 720', 'PC_RES_1': '1366 x 768', 'PC_RES_2': '1600 x 900', 'PC_RES_3': '1920 x 1080',
    'PC_RES_4': '2560 x 1440', 'PC_RES_5': '3440 x 1440', 'PC_RES_6': '3840 x 2160', 'PC_RES_7': 'Desktop Size',
    'PC_FULLSCREEN': 'Fullscreen',
    'PC_FRAME_RATE': 'Frame Rate Limit',
    'PC_LIGHTING': 'Per-Pixel Lighting',
    'PC_SHADOWS': 'Shadows',
    'PC_BLOOM': 'Bloom',
    'PC_FOG': 'Smooth Fog',
    'PC_CONTROLS': 'Gamepad & Mouse',
    'PC_MOUSE_SENS': 'Mouse Sensitivity',
    'PC_MOUSE_INVERT': 'Invert Mouse',
    'PC_GAMEPAD': 'Gamepad',
    'PC_LOOK_X': 'Look Speed Horizontal',
    'PC_LOOK_Y': 'Look Speed Vertical',
    'PC_DEADZONE_L': 'Left Stick Deadzone',
    'PC_DEADZONE_R': 'Right Stick Deadzone',
    'PC_INVERT_Y': 'Invert Look',
    'PC_SCHEME_0': 'Layout: Modern',
    'PC_SCHEME_1': 'Layout: Original',
    'PC_QUIT': 'Quit Game',
}
RESOLUTIONS = 8

# ------------------------------------------------------------ object helpers
REF_KEYS = ('link_to', 'startup_widget', 'path_hash', 'dec_hash', 'inc_hash', 'feedback_hash', 'active_text')

def rehash(obj, path, mapping):
    """Hashes are hash(page/widget/element); renaming or moving an object changes
    its whole subtree. mapping collects old->new for reference fix-up."""
    new = H(path)
    if obj['hash'] != new: mapping[obj['hash']] = new
    obj['hash'] = new
    for c in obj.get('children', []): rehash(c, path + '/' + c['name'], mapping)

def fix_refs(obj, mapping):
    for o in G.walk(obj):
        for k in REF_KEYS:
            if k in o and o[k] in mapping: o[k] = mapping[o[k]]
        if 'nav' in o: o['nav'] = [mapping.get(h, h) for h in o['nav']]

def clone(obj, name, parent_path=None):
    o = copy.deepcopy(obj); o['name'] = name
    mapping = {}
    rehash(o, name if parent_path is None else parent_path + '/' + name, mapping)
    fix_refs(o, mapping)
    return o

def pos(o, x, y):
    o['old_pos'] = [G.fbytes(float(x)), G.fbytes(float(y)), G.fbytes(0.0)]

def text_child(o, child_name, text_id):
    G.find(o, child_name)['text_id'] = H(text_id)

def set_var(o, name): o['console_var'] = {'version': 0, 'name': name}

def chain(widgets, up=2, down=3):
    """Vertical nav list: slots [left, right, up, down]; wraps like the shipped menus."""
    n = len(widgets)
    for i, w in enumerate(widgets):
        w['nav'][up] = widgets[(i - 1) % n]['hash']
        w['nav'][down] = widgets[(i + 1) % n]['hash']

def add_page(gui, after_page, page):
    """Inserts a UIMP chunk right after the chunk holding after_page."""
    for i, c in enumerate(gui.chunks):
        if c.page is not None and c.page['name'] == after_page:
            nc = G.Chunk('UIMP', c.version, c.flags, b''); nc.page = page
            gui.chunks.insert(i + 1, nc); return
    raise KeyError(after_page)

def replace_children(page, keep):
    page['children'] = [c for c in page['children'] if keep(c)]

def condition(o, var, value):
    o['condition_manager'] = {'version': 0, 'operator': 0,
                              'vars': [{'version': 0, 'var': {'version': 0, 'name': var}, 'value': str(value), 'condition': 1}]}

def command(o, name, args='', button=16):
    o['commands'] = {'version': 0, 'actions': [{'button': button, 'cmd': {'version': 0, 'name': name, 'args': args}}]}

# ------------------------------------------------------------ page builders
def video_page(shell_page, name, back_page, src):
    """Video Options: resolution cycler, fullscreen, frame-rate numeric, four render switches."""
    page = clone(shell_page, name)
    replace_children(page, lambda c: c['type'] in (G.T_IMAGE, G.T_TEXTBOX) or c['name'].startswith('E_TX_StyleSelectIcon')
                     or c['name'] == 'W_BU_BackButton')
    text_child(G.find(page, 'W_TB_StyleMenuTitle'), 'E_TX_StyleMenuTitle', 'PC_VIDEO_OPTIONS')
    back = G.find(page, 'W_BU_BackButton'); back['link_to'] = H(back_page)

    res = clone(src['scheme_button'], 'W_BU_Resolution', name)
    pos(res, 30, 70); command(res, 'PC_ResolutionNext'); res['link_to'] = 0
    template = G.find(res, 'E_TX_DefaultControlScheme')
    res['children'] = [c for c in res['children'] if c['name'] not in ('E_TX_DefaultControlScheme', 'E_TX_AlternateControlScheme')]
    for i in range(RESOLUTIONS):
        t = clone(template, 'E_TX_Resolution%d' % i, name + '/W_BU_Resolution')
        t['text_id'] = H('PC_RES_%d' % i); condition(t, 'PC.Resolution', i)
        res['children'].append(t)
    full = clone(src['checkbox'], 'W_CB_Fullscreen', name); pos(full, 30, 100)
    set_var(full, 'PC.Fullscreen'); text_child(full, 'E_IM_StyleCheckBoxText', 'PC_FULLSCREEN')
    fps = clone(src['numeric'], 'W_NU_FrameRate', name); pos(fps, 30, 135)
    set_var(fps, 'PC.FrameRateCap'); fps['minimum'] = G.fbytes(30.0); fps['maximum'] = G.fbytes(240.0); fps['step'] = G.fbytes(10.0)
    fps['display_as_int'] = 1; text_child(fps, 'E_IM_Slider_Text', 'PC_FRAME_RATE')
    switches = []
    for i, (wname, var, tid) in enumerate([('W_CB_Lighting', 'PC.PerPixelLighting', 'PC_LIGHTING'), ('W_CB_Shadows', 'PC.Shadows', 'PC_SHADOWS'),
                                           ('W_CB_Bloom', 'PC.Bloom', 'PC_BLOOM'), ('W_CB_Fog', 'PC.SmoothFog', 'PC_FOG')]):
        cb = clone(src['checkbox'], wname, name); pos(cb, 260, 70 + 30 * i)
        set_var(cb, var); text_child(cb, 'E_IM_StyleCheckBoxText', tid); switches.append(cb)
    left = [res, full, fps]
    for w in left + switches: w['nav'] = [0, 0, 0, 0]
    chain(left); chain(switches)
    for w in (res, full): w['nav'][1] = switches[0]['hash']   # the numeric keeps left/right for its own +/- like the Difficulty box
    for w in switches: w['nav'][0] = left[0]['hash']
    page['children'] += left + switches
    page['startup_widget'] = res['hash']
    return page

def gamepad_page(sens_page, name, back_page, src):
    """Gamepad Settings: the Advanced Controls layout with the PC sliders, invert and layout cycler."""
    page = clone(sens_page, name)
    text_child(G.find(page, 'W_TB_StyleMenuTitle'), 'E_TX_StyleMenuTitle', 'PC_CONTROLS')
    back = [c for c in page['children'] if c['type'] == G.T_BUTTON and c['name'].startswith('W_BU_Back')][0]
    back['link_to'] = H(back_page)
    sliders = [c for c in page['children'] if c['type'] == G.T_SLIDER]
    binds = [('PC.LookSensitivityX', 'PC_LOOK_X'), ('PC.LookSensitivityY', 'PC_LOOK_Y'),
             ('PC.LeftDeadzone', 'PC_DEADZONE_L'), ('PC.RightDeadzone', 'PC_DEADZONE_R')]
    for s, (var, tid) in zip(sliders, binds):
        set_var(s, var); text_child(s, 'E_IM_Slider_Text', tid)
    invert = [c for c in page['children'] if c['type'] == G.T_CHECKBOX][0]
    set_var(invert, 'PC.InvertY'); text_child(invert, 'E_IM_StyleCheckBoxText', 'PC_INVERT_Y')
    for c in page['children']:
        if c['type'] == G.T_TEXT and c['name'] == 'W_TB_Infantry_sensitivity': c['text_id'] = H('PC_GAMEPAD')
    layout = clone(src['scheme_button'], 'W_BU_Layout', name)
    pos(layout, 190, 130); command(layout, 'PC_ControlSchemeNext'); layout['link_to'] = 0
    for tname, value, tid in (('E_TX_DefaultControlScheme', 0, 'PC_SCHEME_0'), ('E_TX_AlternateControlScheme', 1, 'PC_SCHEME_1')):
        t = G.find(layout, tname); t['text_id'] = H(tid); condition(t, 'PC.ControlScheme', value)
    mouse = clone(sliders[0], 'W_SL_MouseSensitivity', name); pos(mouse, 190, 170)
    set_var(mouse, 'PC.MouseSensitivity'); text_child(mouse, 'E_IM_Slider_Text', 'PC_MOUSE_SENS')
    minvert = clone(invert, 'W_CB_MouseInvert', name); pos(minvert, 190, 212)
    set_var(minvert, 'PC.MouseInvertY'); text_child(minvert, 'E_IM_StyleCheckBoxText', 'PC_MOUSE_INVERT')
    page['children'] += [layout, mouse, minvert]
    right = [invert, layout, mouse, minvert]
    for w in sliders + right: w['nav'] = [0, 0, 0, 0]
    chain(sliders); chain(right)
    for w in sliders: w['nav'][1] = invert['hash']
    for w in right: w['nav'][0] = sliders[0]['hash']
    page['startup_widget'] = sliders[0]['hash']
    return page

def quit_page(main_page, question_text, name, back_page):
    """Quit confirmation built from the main menu's own elements (its button and
    title styles are the ones loaded in the front end), laid out like the
    Profile prompt: title, question, two buttons."""
    page = clone(main_page, name)
    page['page_flags'] = 7  # back allowed, closes this page
    drop = {'Group 1', 'W_TLB_VersionNumber', 'TextListbox 1', 'W_TB_StyleSelect 1', 'W_TB_StyleMenuTitle 1', 'E_TX_StyleSelectIcon 2'}
    movies = G.find(page, 'W_BU_MMMovies')
    replace_children(page, lambda c: not c['name'].startswith('W_BU_MM') and c['name'] not in drop)
    text_child(G.find(page, 'W_TB_StyleMenuTitle'), 'E_TX_StyleMenuTitle', 'PC_QUIT')
    question = clone(question_text, 'E_TX_QuitQuestion', name)
    question['text_id'] = H('IG_ARE_YOU_SURE'); pos(question, 11, 141)
    yes = clone(movies, 'W_BU_QuitYes', name); pos(yes, 18, 168)
    yes['link_to'] = 0; command(yes, 'PC_QuitGame'); text_child(yes, 'E_TX_StyleButtonText', 'IG_YES')
    no = clone(movies, 'W_BU_QuitNo', name); pos(no, 18, 200)
    no['link_to'] = H(back_page); no['commands'] = {'version': 0, 'actions': []}; text_child(no, 'E_TX_StyleButtonText', 'IG_NO')
    for w in (yes, no): w['nav'] = [0, 0, 0, 0]
    chain([yes, no])
    page['children'] += [question, yes, no]
    page['startup_widget'] = no['hash']
    return page

# ------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--game', default=r'C:\Games\Star Wars Renegade Squadron\data\PSP_GAME\USRDIR')
    ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'mods-pc', 'files'))
    a = ap.parse_args()
    gui_dir = os.path.join(a.game, 'GUIMENU'); out_gui = os.path.join(a.out, 'PSP_GAME', 'USRDIR', 'GUIMENU')
    os.makedirs(out_gui, exist_ok=True)
    load = lambda n: G.GuiFile(open(os.path.join(gui_dir, n), 'rb').read())
    options, ingame, mainmenu = load('BFF_OPTIONS.GUI'), load('BFF_GUIMENU_INGAMESP.GUI'), load('BFF_MAINMENU.GUI')

    # widget templates (styles are global; these are the shipped widgets of each kind)
    fe_controls = options.page('MP_Controls_FrontEnd')
    src = {'scheme_button': G.find(fe_controls, 'W_BU_ControlScheme'),
           'checkbox': G.find(options.page('MP_AudioOptions_FrontEnd'), 'W_CB_Subtitles'),
           'numeric': G.find(options.page('MP_Gameoptions'), 'W_NU_AIDifficulty')}

    # --- front end Options: Video Options button + page
    fe_opts = options.page('MP_Options_FrontEnd')
    audio_btn = G.find(fe_opts, 'W_BU_AudioOptions')
    video_btn = clone(audio_btn, 'W_BU_VideoOptions', 'MP_Options_FrontEnd')
    video_btn['link_to'] = H('MP_VideoOptions_FrontEnd'); text_child(video_btn, 'E_TX_StyleButtonText', 'PC_VIDEO_OPTIONS')
    order = ['W_BU_Controls', 'W_BU_AIDifficulty', 'W_BU_AudioOptions', 'W_BU_VideoOptions', 'W_BU_ProfileManagement 1', 'W_BU_Medals', 'W_BU_ProfileManagement']
    fe_opts['children'].insert(fe_opts['children'].index(audio_btn) + 1, video_btn)
    buttons = {c['name']: c for c in fe_opts['children'] if c['type'] == G.T_BUTTON}
    for i, n in enumerate(order): pos(buttons[n], 30, 70 + 26 * i)
    chain([buttons[n] for n in order])
    add_page(options, 'MP_AudioOptions_FrontEnd',
             video_page(options.page('MP_AudioOptions_FrontEnd'), 'MP_VideoOptions_FrontEnd', 'MP_Options_FrontEnd', src))

    # --- front end Controls: Gamepad Settings button + page
    sens_btn = G.find(fe_controls, 'W_BU_StyleButtonControlsSensitivity')
    pad_btn = clone(sens_btn, 'W_BU_PCControls', 'MP_Controls_FrontEnd')
    pad_btn['link_to'] = H('MP_PCControls_FrontEnd'); text_child(pad_btn, 'E_TX_StyleButtonText', 'PC_CONTROLS'); pos(pad_btn, 30, 220)
    fe_controls['children'].insert(fe_controls['children'].index(sens_btn) + 1, pad_btn)
    corder = ['W_BU_ControlScheme', 'W_BU_StyleButtonInfantryControls', 'W_BU_StyleButtonVehicleControls',
              'W_BU_StyleButtonSpacecraftControls', 'W_BU_StyleButtonControlsSensitivity', 'W_BU_PCControls']
    chain([G.find(fe_controls, n) for n in corder])
    add_page(options, 'MP_ControlsSensitivity',
             gamepad_page(options.page('MP_ControlsSensitivity'), 'MP_PCControls_FrontEnd', 'MP_Controls_FrontEnd', src))

    # --- in-game Options / Controls
    ig_opts = ingame.page('MP_Options_InGame')
    ig_audio = G.find(ig_opts, 'W_BU_AudioOptions'); ig_ctrl = G.find(ig_opts, 'W_BU_Controls')
    ig_video = clone(ig_audio, 'W_BU_VideoOptions', 'MP_Options_InGame')
    ig_video['link_to'] = H('MP_VideoOptions_InGame'); text_child(ig_video, 'E_TX_StyleButtonText', 'PC_VIDEO_OPTIONS'); pos(ig_video, 30, 130)
    ig_opts['children'].insert(ig_opts['children'].index(ig_ctrl) + 1, ig_video)
    chain([ig_audio, ig_ctrl, ig_video])
    add_page(ingame, 'MP_AudioOptions_InGame',
             video_page(ingame.page('MP_AudioOptions_InGame'), 'MP_VideoOptions_InGame', 'MP_Options_InGame', src))
    ig_controls = ingame.page('MP_Controls_InGame')
    ig_sens = G.find(ig_controls, 'W_BU_StyleButtonControlsSensitivity')
    ig_pad = clone(ig_sens, 'W_BU_PCControls', 'MP_Controls_InGame')
    ig_pad['link_to'] = H('MP_PCControls_InGame'); text_child(ig_pad, 'E_TX_StyleButtonText', 'PC_CONTROLS')
    ig_controls['children'].append(ig_pad)
    igorder = ['W_BU_ControlScheme', 'W_BU_StyleButtonInfantryControls', 'W_BU_StyleButtonVehicleControls',
               'W_BU_StyleButtonVehicleControls 1', 'W_BU_StyleButtonControlsSensitivity', 'W_BU_PCControls']
    igb = [G.find(ig_controls, n) for n in igorder]
    for i, b in enumerate(igb): pos(b, 29, 75 + 30 * i)
    chain(igb)
    add_page(ingame, 'MP_ControlsSensitivity_InGame',
             gamepad_page(ingame.page('MP_ControlsSensitivity_InGame'), 'MP_PCControls_InGame', 'MP_Controls_InGame', src))

    # --- main menu: Quit Game + confirmation page
    mm = mainmenu.page('MP_MainMenu')
    movies = G.find(mm, 'W_BU_MMMovies')
    quit_btn = clone(movies, 'W_BU_MMQuit', 'MP_MainMenu')
    quit_btn['link_to'] = H('MP_PCQuit'); text_child(quit_btn, 'E_TX_StyleButtonText', 'PC_QUIT')
    mm['children'].insert(mm['children'].index(movies) + 1, quit_btn)
    mmb = [G.find(mm, n) for n in ('W_BU_MMSinglePlayer', 'W_BU_MMMultiPlayer', 'W_BU_MMCustomisation', 'W_BU_MMOptions', 'W_BU_MMMovies', 'W_BU_MMQuit')]
    for i, b in enumerate(mmb): pos(b, 20, 113 + 24 * i)  # six rows above the version number line
    chain(mmb)
    profile = load('BFF_PROFILE.GUI')
    add_page(mainmenu, 'MP_MainMenu', quit_page(mainmenu.page('MP_MainMenu'), G.find(profile.page('MP_Profile'), 'Text 1'), 'MP_PCQuit', 'MP_MainMenu'))

    for fname, gui in (('BFF_OPTIONS.GUI', options), ('BFF_GUIMENU_INGAMESP.GUI', ingame), ('BFF_MAINMENU.GUI', mainmenu)):
        data = gui.encode()
        G.GuiFile(data)  # must parse back
        open(os.path.join(out_gui, fname), 'wb').write(data)
        print('wrote', fname, len(data), 'bytes', [p['name'] for p in gui.pages() if p['name'].startswith(('MP_Video', 'MP_PC'))])

    # --- menu text
    f, pages = T.load_menu_text(os.path.join(a.game, 'MISC', 'MENU', 'MENU_AM.ASR'))
    for i, page in pages:
        if page.page_id == MENU_TEXT_PAGE:
            for tid, s in TEXTS.items(): page.set(tid, s)
    T.save_menu_text(f, pages, os.path.join(a.out, 'PSP_GAME', 'USRDIR', 'MISC', 'MENU', 'MENU_AM.ASR'))
    print('wrote MENU_AM.ASR with', len(TEXTS), 'new strings')

if __name__ == '__main__':
    main()
