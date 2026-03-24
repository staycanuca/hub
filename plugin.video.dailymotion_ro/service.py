from kodi_six import xbmc, xbmcaddon
import time
import json
from resources.lib import dailymotion as dm

addon = xbmcaddon.Addon()
addonID = addon.getAddonInfo('id')

def _load_state():
    try:
        from kodi_six import xbmcvfs
        path = xbmcvfs.translatePath('special://profile/addon_data/{0}/auto_update.json'.format(addonID))
        if xbmcvfs.exists(path):
            with xbmcvfs.File(path, 'r') as f:
                data = f.read()
                if data:
                    return json.loads(data)
    except Exception:
        pass
    return {"last_run": 0, "in_progress": False}

def _save_state(state):
    from kodi_six import xbmcvfs
    path = xbmcvfs.translatePath('special://profile/addon_data/{0}/auto_update.json'.format(addonID))
    try:
        if not xbmcvfs.exists(xbmcvfs.translatePath('special://profile/addon_data/{0}/'.format(addonID))):
            xbmcvfs.mkdirs(xbmcvfs.translatePath('special://profile/addon_data/{0}/'.format(addonID)))
        with xbmcvfs.File(path, 'w') as f:
            f.write(json.dumps(state))
    except Exception:
        xbmc.log('Dailymotion: failed saving auto_update.json', xbmc.LOGERROR)

def should_run(now_ts, state):
    interval = addon.getSetting('auto_update_interval')  # 0:startup,1:hourly,2:6h,3:daily
    if interval == '0':
        # Run once per boot
        return state.get('last_run', 0) == 0
    elif interval == '1':
        return now_ts - state.get('last_run', 0) >= 3600
    elif interval == '2':
        return now_ts - state.get('last_run', 0) >= 21600
    elif interval == '3':
        # Run when localtime hour matches target and not run in last 20 hours
        try:
            target_hour = int(addon.getSetting('auto_update_hour') or '3')
        except Exception:
            target_hour = 3
        hour = time.localtime().tm_hour
        return (hour == target_hour) and (now_ts - state.get('last_run', 0) >= 20*3600)
    return False

def run_update():
    full_scan = (addon.getSetting('auto_update_mode') == '1')
    try:
        dm.auto_update_from_users_file(full_scan=full_scan, silent=True)
    except Exception as e:
        xbmc.log('Dailymotion: auto update error: {0}'.format(e), xbmc.LOGERROR)

if __name__ == '__main__':
    try:
        if addon.getSetting('auto_update_enabled') != 'true':
            xbmc.Monitor().waitForAbort(300)
        state = _load_state()
        monitor = xbmc.Monitor()
        # initial delay to let UI settle
        monitor.waitForAbort(10)
        while not monitor.abortRequested():
            now_ts = int(time.time())
            if addon.getSetting('auto_update_enabled') == 'true' and not state.get('in_progress', False) and should_run(now_ts, state):
                xbmc.log('Dailymotion: starting auto update (full_scan={0})'.format(addon.getSetting('auto_update_mode')=='1'), xbmc.LOGDEBUG)
                state['in_progress'] = True
                _save_state(state)
                run_update()
                state['last_run'] = int(time.time())
                state['in_progress'] = False
                _save_state(state)
            # sleep 60s between checks
            if monitor.waitForAbort(60):
                break
    except Exception as e:
        xbmc.log('Dailymotion: service crashed: {0}'.format(e), xbmc.LOGERROR)
