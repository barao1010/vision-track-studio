-- SPDX-License-Identifier: GPL-2.0-or-later
-- Identical production exercise for upstream OBS and Vision Track Studio.
obs = obslua
local root = script_path()
local scenes = {}
local step = 0
local results = {}

function result(key, value)
    results[key] = value
end

function tick()
    step = step + 1
    if step == 1 then
        local tone = obs.obs_data_create()
        obs.obs_data_set_string(tone, "local_file", root .. "tone.wav")
        obs.obs_data_set_bool(tone, "is_local_file", true)
        obs.obs_data_set_bool(tone, "looping", true)
        local audio = obs.obs_source_create("ffmpeg_source", "Parity Audio", tone, nil)
        obs.obs_data_release(tone)
        if audio ~= nil then
            obs.obs_source_set_audio_mixers(audio, 1)
            obs.obs_source_set_volume(audio, 0.8)
        end
        local settings = obs.obs_data_create()
        obs.obs_data_set_int(settings, "width", 640)
        obs.obs_data_set_int(settings, "height", 360)
        obs.obs_data_set_int(settings, "color", 4281558732)
        local color = obs.obs_source_create("color_source_v3", "Parity Color", settings, nil)
        obs.obs_data_release(settings)
        settings = obs.obs_data_create()
        obs.obs_data_set_string(settings, "file", root .. "image.png")
        local image = obs.obs_source_create("image_source", "Parity Image", settings, nil)
        obs.obs_data_release(settings)
        settings = obs.obs_data_create()
        obs.obs_data_set_bool(settings, "is_local_file", true)
        obs.obs_data_set_string(settings, "local_file", root .. "browser.html")
        obs.obs_data_set_int(settings, "width", 640)
        obs.obs_data_set_int(settings, "height", 360)
        obs.obs_data_set_string(settings, "css", "body { margin:0; overflow:hidden; }")
        local browser = obs.obs_source_create("browser_source", "Parity Browser", settings, nil)
        obs.obs_data_release(settings)
        result("color", color ~= nil)
        result("image", image ~= nil)
        result("browser", browser ~= nil)
        result("audio", audio ~= nil)
        for i, source in ipairs({color, image, browser}) do
            local scene = obs.obs_scene_create("Parity " .. i)
            scenes[i] = scene
            if source ~= nil then obs.obs_scene_add(scene, source) end
            if audio ~= nil then obs.obs_scene_add(scene, audio) end
        end
        if color ~= nil then obs.obs_source_release(color) end
        if image ~= nil then obs.obs_source_release(image) end
        if browser ~= nil then obs.obs_source_release(browser) end
        if audio ~= nil then obs.obs_source_release(audio) end
        local fade = obs.obs_source_create_private("fade_transition", "Parity Fade", nil)
        if fade ~= nil then
            obs.obs_frontend_set_current_transition(fade)
            obs.obs_frontend_set_transition_duration(300)
            obs.obs_source_release(fade)
        end
        result("fade", fade ~= nil)
        obs.obs_frontend_set_current_scene(obs.obs_scene_get_source(scenes[1]))
    elseif step == 2 then
        obs.obs_frontend_recording_start()
    elseif step == 3 then
        result("recording", obs.obs_frontend_recording_active())
        obs.obs_frontend_set_current_scene(obs.obs_scene_get_source(scenes[2]))
    elseif step == 4 then
        obs.obs_frontend_set_current_scene(obs.obs_scene_get_source(scenes[3]))
    elseif step == 5 then
        obs.obs_frontend_recording_stop()
    elseif step == 6 then
        result("stopped", not obs.obs_frontend_recording_active())
        local file = io.open(root .. "exercise.json", "w")
        if file then
            file:write("{")
            local first = true
            for key, value in pairs(results) do
                if not first then file:write(",") end
                first = false
                file:write('"' .. key .. '":' .. tostring(value))
            end
            file:write("}")
            file:close()
        end
        obs.timer_remove(tick)
    end
end

function on_event(event)
    if event == obs.OBS_FRONTEND_EVENT_FINISHED_LOADING then obs.timer_add(tick, 3500) end
end

function script_load(settings)
    obs.obs_frontend_add_event_callback(on_event)
end

function script_unload()
    obs.timer_remove(tick)
    for _, scene in ipairs(scenes) do obs.obs_scene_release(scene) end
end
