#!/usr/bin/env python3


# Required dependencies:
# pip install pygame numpy pydub inaSpeechSegmenter tqdm scipy
# System requirement: ffmpeg installed and available in PATH

import argparse
import os
import copy
import wave
import numpy as np
import pygame
from pydub import AudioSegment
from inaSpeechSegmenter import Segmenter
from tqdm import tqdm


def main():
    parser = argparse.ArgumentParser(description="Band Rehearsal Segmenter UI")
    parser.add_argument("input", help="Input audio file")
    args = parser.parse_args()

    input_file = args.input
    temp_wav = "temp_working_audio.wav"

    # 1. Audio Processing & Conversion
    print("Loading and converting audio to mono WAV...")
    audio = AudioSegment.from_file(input_file).set_channels(1)
    audio.export(temp_wav, format="wav")

    # 2. Run inaSpeechSegmenter
    print("Running speech/music/noise segmentation...")
    segmenter = Segmenter(vad_engine='smn', detect_gender=False)
    raw_segments = segmenter(temp_wav)

    segments = []
    seg_idx = 1
    for label, start, end in raw_segments:
        if label == 'music':
            segments.append({
                'name': f'audio{seg_idx}',
                'start': start,
                'end': end,
                'selected': False
            })
            seg_idx += 1

    # 3. Waveform Generation for UI
    print("Extracting waveform envelope...")
    wav = wave.open(temp_wav, 'r')
    framerate = wav.getframerate()
    nframes = wav.getnframes()
    raw_data = wav.readframes(nframes)
    wav.close()

    audio_data = np.frombuffer(raw_data, dtype=np.int16)

    fps = 60
    samples_per_frame = framerate // fps
    num_frames = len(audio_data) // samples_per_frame

    env_min = np.zeros(num_frames)
    env_max = np.zeros(num_frames)

    for i in tqdm(range(num_frames), desc="Building visualization data"):
        chunk = audio_data[i * samples_per_frame: (i + 1) * samples_per_frame]
        if len(chunk) > 0:
            env_min[i] = chunk.min()
            env_max[i] = chunk.max()

    max_amp = float(max(abs(env_min.min()), abs(env_max.max())))
    if max_amp == 0: max_amp = 1.0

    # 4. Pygame UI Setup
    pygame.init()
    W, H = 1200, 400
    screen = pygame.display.set_mode((W, H), pygame.RESIZABLE)
    pygame.display.set_caption("Segment Editor")
    font = pygame.font.SysFont(None, 24)
    pygame.mixer.init(frequency=framerate)
    pygame.mixer.music.load(temp_wav)

    # UI State variables
    view_start = 0.0
    px_per_sec = 100.0
    play_pos = 0.0
    playing = False
    play_start_pos = 0.0
    undo_stack = [copy.deepcopy(segments)]

    def save_state():
        undo_stack.append(copy.deepcopy(segments))

    # Interaction states
    drag_mode = None
    active_seg = None
    box_start = None
    box_current = None
    edit_segment = None
    last_click_time = 0

    clock = pygame.time.Clock()
    running = True

    while running:
        # Calculate precise current playhead
        if playing:
            current_pos = play_start_pos + (pygame.mixer.music.get_pos() / 1000.0)
        else:
            current_pos = play_pos

        mods = pygame.key.get_mods()
        ctrl = mods & pygame.KMOD_CTRL
        shift = mods & pygame.KMOD_SHIFT

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            elif event.type == pygame.VIDEORESIZE:
                W, H = event.w, event.h
                screen = pygame.display.set_mode((W, H), pygame.RESIZABLE)

            elif event.type == pygame.MOUSEWHEEL:
                if ctrl:
                    zoom_factor = 1.1 ** event.y
                    mouse_x = pygame.mouse.get_pos()[0]
                    mouse_time = view_start + (mouse_x / px_per_sec)
                    px_per_sec *= zoom_factor
                    px_per_sec = max(5.0, min(px_per_sec, 2000.0))
                    view_start = mouse_time - (mouse_x / px_per_sec)
                else:
                    view_start -= event.x * (50 / px_per_sec)
                    view_start -= event.y * (50 / px_per_sec)
                view_start = max(0.0, view_start)

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if edit_segment:
                    edit_segment = None  # Drop focus

                if event.button == 1:  # Left click
                    mouse_x, mouse_y = event.pos
                    mouse_time = view_start + (mouse_x / px_per_sec)

                    clicked_seg = None
                    edge_clicked = None
                    margin = 5 / px_per_sec  # 5 pixels margin for edge

                    # Hit testing segments
                    for seg in segments:
                        if seg['start'] - margin <= mouse_time <= seg['end'] + margin:
                            clicked_seg = seg
                            if abs(mouse_time - seg['start']) <= margin:
                                edge_clicked = 'left'
                            elif abs(mouse_time - seg['end']) <= margin:
                                edge_clicked = 'right'
                            else:
                                edge_clicked = 'center'
                            break

                    if clicked_seg:
                        now = pygame.time.get_ticks()
                        if edge_clicked == 'center' and (now - last_click_time) < 300:
                            edit_segment = clicked_seg
                        last_click_time = now

                        if not clicked_seg['selected'] and not (ctrl or shift):
                            for s in segments: s['selected'] = False
                        clicked_seg['selected'] = True

                        active_seg = clicked_seg
                        drag_mode = edge_clicked
                    else:
                        if not (ctrl or shift):
                            for s in segments: s['selected'] = False
                        drag_mode = 'box'
                        box_start = (mouse_x, mouse_y)
                        box_current = box_start

            elif event.type == pygame.MOUSEMOTION:
                mouse_x, mouse_y = event.pos
                mouse_time = view_start + (mouse_x / px_per_sec)

                if drag_mode in ['left', 'right', 'center']:
                    dt = mouse_time - (view_start + (event.pos[0] - event.rel[0]) / px_per_sec)
                    if drag_mode == 'center':
                        for seg in segments:
                            if seg['selected']:
                                seg['start'] = max(0, seg['start'] + dt)
                                seg['end'] += dt
                    elif drag_mode == 'left':
                        active_seg['start'] = min(max(0, active_seg['start'] + dt), active_seg['end'] - 0.1)
                    elif drag_mode == 'right':
                        active_seg['end'] = max(active_seg['start'] + 0.1, active_seg['end'] + dt)

                elif drag_mode == 'box':
                    box_current = (mouse_x, mouse_y)

            elif event.type == pygame.MOUSEBUTTONUP:
                if event.button == 1:
                    if drag_mode in ['left', 'right', 'center']:
                        save_state()
                    elif drag_mode == 'box' and box_start and box_current:
                        x1, x2 = sorted([box_start[0], box_current[0]])
                        t1 = view_start + (x1 / px_per_sec)
                        t2 = view_start + (x2 / px_per_sec)
                        for seg in segments:
                            if (seg['start'] <= t2 and seg['end'] >= t1):
                                seg['selected'] = True
                        box_start = None
                        box_current = None
                    drag_mode = None
                    active_seg = None

            elif event.type == pygame.KEYDOWN:
                if edit_segment:
                    if event.key == pygame.K_RETURN or event.key == pygame.K_ESCAPE:
                        edit_segment = None
                        save_state()
                    elif event.key == pygame.K_BACKSPACE:
                        edit_segment['name'] = edit_segment['name'][:-1]
                    else:
                        edit_segment['name'] += event.unicode
                    continue

                if event.key == pygame.K_SPACE:
                    if playing:
                        pygame.mixer.music.stop()
                        play_pos = current_pos
                    else:
                        play_pos = current_pos
                        pygame.mixer.music.play(start=play_pos)
                        play_start_pos = play_pos
                    playing = not playing

                elif event.key == pygame.K_h and ctrl:
                    skip = 1.0 if shift else 3.0
                    new_pos = max(0, current_pos - skip)
                    if playing:
                        pygame.mixer.music.play(start=new_pos)
                        play_start_pos = new_pos
                    else:
                        play_pos = new_pos

                elif event.key == pygame.K_l and ctrl:
                    skip = 1.0 if shift else 3.0
                    new_pos = current_pos + skip
                    if playing:
                        pygame.mixer.music.play(start=new_pos)
                        play_start_pos = new_pos
                    else:
                        play_pos = new_pos

                elif event.key == pygame.K_d:
                    segments = [s for s in segments if not s['selected']]
                    save_state()

                elif event.key == pygame.K_n:
                    used_ns = [int(s['name'][5:]) for s in segments if
                               s['name'].startswith('audio') and s['name'][5:].isdigit()]
                    next_n = max(used_ns) + 1 if used_ns else 1
                    segments.append({
                        'name': f'audio{next_n}',
                        'start': current_pos,
                        'end': current_pos + 1.0,
                        'selected': True
                    })
                    save_state()

                elif event.key == pygame.K_f:
                    margin = 2.0
                    view_start = max(0, current_pos - margin)

                elif event.key == pygame.K_h and not ctrl:
                    view_start = max(0, view_start - 3.0)

                elif event.key == pygame.K_l and not ctrl:
                    view_start += 3.0

                elif event.key == pygame.K_j:
                    future_segs = [s for s in segments if s['start'] > current_pos + 0.1]
                    if future_segs:
                        next_seg = min(future_segs, key=lambda s: s['start'])
                        if playing: pygame.mixer.music.play(start=next_seg['start'])
                        play_start_pos = next_seg['start']
                        play_pos = next_seg['start']

                elif event.key == pygame.K_k:
                    past_segs = [s for s in segments if s['start'] < current_pos - 0.1]
                    if past_segs:
                        prev_seg = max(past_segs, key=lambda s: s['start'])
                        if playing: pygame.mixer.music.play(start=prev_seg['start'])
                        play_start_pos = prev_seg['start']
                        play_pos = prev_seg['start']

                elif event.key == pygame.K_z and ctrl:
                    if len(undo_stack) > 1:
                        undo_stack.pop()
                        segments = copy.deepcopy(undo_stack[-1])

                elif event.key == pygame.K_e and ctrl:
                    base_name = os.path.splitext(os.path.basename(input_file))[0]
                    out_dir = f"output/{base_name}"
                    counter = 1
                    while os.path.exists(out_dir):
                        out_dir = f"output/{base_name}-{counter}"
                        counter += 1
                    os.makedirs(out_dir)
                    print(f"\nExporting {len(segments)} segments to {out_dir} ...")
                    for s in segments:
                        s_ms = int(s['start'] * 1000)
                        e_ms = int(s['end'] * 1000)
                        chunk = audio[s_ms:e_ms]
                        out_path = os.path.join(out_dir, f"{s['name']}.wav")
                        chunk.export(out_path, format="wav")
                    print("Export complete.")

        # Rendering
        screen.fill((240, 240, 240))

        # Draw Timeline Header
        pygame.draw.rect(screen, (220, 220, 220), (0, 0, W, 40))
        pygame.draw.line(screen, (0, 0, 0), (0, 40), (W, 40), 1)

        # Timeline markers
        view_end = view_start + (W / px_per_sec)
        first_tick = int(view_start)
        for t in range(first_tick, int(view_end) + 1):
            x = (t - view_start) * px_per_sec
            pygame.draw.line(screen, (150, 150, 150), (x, 25), (x, 40))
            if t % 15 == 0:
                txt = font.render(str(t), True, (0, 0, 0))
                screen.blit(txt, (x + 2, 5))

        # Draw Waveform
        start_frame = max(0, int(view_start * fps))
        end_frame = min(num_frames, int(view_end * fps) + 1)

        mid_y = H / 2 + 20
        amp_scale = (H / 2 - 40) / max_amp

        for i in range(start_frame, end_frame):
            t = i / fps
            x = (t - view_start) * px_per_sec
            next_x = ((t + 1 / fps) - view_start) * px_per_sec
            width = max(1, int(next_x - x))

            y_min = mid_y - (env_max[i] * amp_scale)
            y_max = mid_y - (env_min[i] * amp_scale)

            pygame.draw.rect(screen, (100, 100, 200), (x, y_min, width, max(1, y_max - y_min)))

        # Draw transparent segment blocks as in image_b8473c.png[cite: 1]
        overlay = pygame.Surface((W, H), pygame.SRCALPHA)
        for seg in segments:
            x1 = (seg['start'] - view_start) * px_per_sec
            x2 = (seg['end'] - view_start) * px_per_sec
            if x2 > 0 and x1 < W:
                rect = (x1, 41, x2 - x1, H - 41)
                color = (255, 100, 100, 100) if not seg['selected'] else (255, 50, 50, 150)
                pygame.draw.rect(overlay, color, rect)
                if seg['selected']:
                    pygame.draw.rect(screen, (255, 0, 0), rect, 2)

                name_txt = seg['name']
                if edit_segment == seg:
                    name_txt += "_"

                txt_surf = font.render(name_txt, True, (0, 0, 0))
                screen.blit(txt_surf, (max(0, x1) + 5, 45))

        screen.blit(overlay, (0, 0))

        # Draw box selection
        if drag_mode == 'box' and box_start and box_current:
            x1, y1 = box_start
            x2, y2 = box_current
            box_rect = (min(x1, x2), min(y1, y2), abs(x2 - x1), abs(y2 - y1))
            pygame.draw.rect(screen, (100, 100, 255), box_rect, 1)

        # Draw Playhead
        ph_x = (current_pos - view_start) * px_per_sec
        if 0 <= ph_x <= W:
            pygame.draw.line(screen, (255, 0, 0), (ph_x, 0), (ph_x, H), 2)

        pygame.display.flip()
        clock.tick(30)

    pygame.quit()
    if os.path.exists(temp_wav):
        os.remove(temp_wav)


if __name__ == "__main__":
    main()