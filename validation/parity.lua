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
        -- Load the exact same saved collection through the normal OBS loader.
        -- Creating scenes inside Lua's timer can re-enter frontend event callbacks.
        for _, entry in ipairs({{"color","Parity Color"},{"image","Parity Image"},{"browser","Parity Browser"},{"audio","Parity Audio"}}) do
            local source = obs.obs_get_source_by_name(entry[2])
            result(entry[1], source ~= nil)
            if source ~= nil then obs.obs_source_release(source) end
        end
        for i=1,3 do
            scenes[i] = obs.obs_get_source_by_name("Parity " .. i)
        end
        local transition = obs.obs_frontend_get_current_transition()
        result("fade", transition ~= nil and obs.obs_source_get_unversioned_id(transition) == "fade_transition")
        if transition ~= nil then obs.obs_source_release(transition) end
        obs.obs_frontend_set_current_scene(scenes[1])
    elseif step == 2 then
        obs.obs_frontend_recording_start()
    elseif step == 3 then
        result("recording", obs.obs_frontend_recording_active())
        obs.obs_frontend_set_current_scene(scenes[2])
    elseif step == 4 then
        obs.obs_frontend_set_current_scene(scenes[3])
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
    for _, scene in ipairs(scenes) do obs.obs_source_release(scene) end
end
