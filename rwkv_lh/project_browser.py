"""Model-requested browser operations and actual evidence, never project acceptance.

The same file supplies the Harness schema and runs as a trusted standalone worker
in the launch namespace. Candidate code cannot replace this worker or its input.
"""
import asyncio
import json
from pathlib import Path
import sys
import time
from urllib.parse import urljoin, urlsplit


def _operation(action, **fields):
    return {'type': 'object', 'additionalProperties': False,
            'properties': {'action': {'const': action, 'type': 'string'}, **fields},
            'required': ['action', *fields]}


_SELECTOR = {'type': 'string', 'minLength': 1,
             'description': 'Playwright locator selector, for example button or [aria-label="Save"].'}
_TEXT = {'type': 'string'}
BROWSER_STEPS_SCHEMA = {
    'type': 'array', 'default': [],
    'description': 'Optional real Chromium actions/assertions in order; starts at the project URL. '
                   'Fresh browser storage per call. Screenshots, DOM/layout, console and network evidence are retained. '
                   'Only this project origin is reachable; failures stop the sequence. Assertions test only what you request.',
    'items': {'anyOf': [
        _operation('goto', path={'type': 'string', 'minLength': 1}),
        _operation('click', selector=_SELECTOR),
        _operation('fill', selector=_SELECTOR, text=_TEXT),
        _operation('press', selector=_SELECTOR, key={'type': 'string', 'minLength': 1}),
        _operation('select', selector=_SELECTOR, value=_TEXT),
        _operation('check', selector=_SELECTOR, checked={'type': 'boolean'}),
        _operation('expect_text', selector=_SELECTOR, text=_TEXT),
        _operation('expect_count', selector=_SELECTOR, count={'type': 'integer', 'minimum': 0}),
        _operation('expect_visible', selector=_SELECTOR, visible={'type': 'boolean'}),
        _operation('expect_checked', selector=_SELECTOR, checked={'type': 'boolean'}),
        _operation('reload'),
        _operation('viewport', width={'type': 'integer', 'minimum': 240, 'maximum': 3840},
                   height={'type': 'integer', 'minimum': 240, 'maximum': 2160}),
        _operation('inspect', selector=_SELECTOR),
        _operation('screenshot'),
    ]},
}


_ELEMENTS = '''elements => elements.map(element => {
    const box = element.getBoundingClientRect(), css = getComputedStyle(element);
    return {tag: element.tagName.toLowerCase(), role: element.getAttribute('role'),
        label: element.getAttribute('aria-label'), text: element.innerText ?? element.textContent,
        value: element.value ?? null, checked: element.checked ?? null,
        visible: Boolean(element.getClientRects().length) && css.visibility !== 'hidden',
        bounds: {x: box.x, y: box.y, width: box.width, height: box.height},
        style: {color: css.color, backgroundColor: css.backgroundColor, fontSize: css.fontSize}};
})'''


def _origin(value):
    parsed = urlsplit(value)
    return parsed.scheme, parsed.hostname, parsed.port


async def run_browser(spec, output):
    from playwright.async_api import async_playwright, expect
    deadline = time.monotonic() + spec['timeout']
    result = dict(status='running', steps=[], assertions_passed=0, console=[], page_errors=[],
                  network=[], snapshot=None, browser_version=None, error=None)
    journal = output / 'JOURNAL.json'

    def save():
        stage = output / 'JOURNAL.tmp'
        stage.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n')
        stage.replace(journal)

    def remaining_ms():
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise TimeoutError('browser time budget exhausted')
        return max(1, min(5000, remaining * 1000))

    origin = _origin(spec['url'])
    save()
    async with async_playwright() as p:
        browser = context = page = None
        try:
            browser = await p.chromium.launch(headless=True, timeout=remaining_ms())
            result['browser_version'] = browser.version
            context = await browser.new_context(viewport={'width': 1280, 'height': 900},
                accept_downloads=False, service_workers='block', record_har_path=str(output / 'network.har'))
            await context.tracing.start(screenshots=True, snapshots=True, sources=False)

            async def route_request(route):
                url = route.request.url
                if _origin(url) == origin:
                    await route.continue_()
                else:
                    result['network'].append({'url': url, 'blocked': True, 'reason': 'outside_project_origin'})
                    await route.abort('blockedbyclient')
                save()

            await context.route('**/*', route_request)
            async def route_socket(route):
                scheme, host, port = _origin(route.url)
                socket_origin = ({'ws': 'http', 'wss': 'https'}.get(scheme, scheme), host, port)
                blocked = socket_origin != origin
                result['network'].append({'url': route.url, 'kind': 'websocket', 'blocked': blocked})
                if blocked:
                    await route.close(code=1008, reason='outside_project_origin')
                else:
                    route.connect_to_server()
                save()
            await context.route_web_socket('**/*', route_socket)
            page = await context.new_page()
            page.on('console', lambda message: result['console'].append({'type': message.type, 'text': message.text}))
            page.on('pageerror', lambda error: result['page_errors'].append(str(error)))
            page.on('response', lambda response: result['network'].append({
                'url': response.url, 'status': response.status, 'kind': response.request.resource_type}))
            page.on('requestfailed', lambda request: result['network'].append({
                'url': request.url, 'failure': request.failure, 'kind': request.resource_type}))
            await page.goto(spec['url'], wait_until='load', timeout=remaining_ms())
            for index, action in enumerate(spec['steps']):
                row = {'index': index, 'action': action, 'status': 'running'}
                result['steps'].append(row)
                save()
                try:
                    timeout = remaining_ms()
                    page.set_default_timeout(timeout)
                    locator = page.locator(action['selector']) if 'selector' in action else None
                    kind = action['action']
                    if kind == 'goto':
                        url = urljoin(spec['url'] + '/', action['path'])
                        if _origin(url) != origin:
                            raise ValueError('navigation must stay within the project origin')
                        await page.goto(url, wait_until='load', timeout=timeout)
                    elif kind == 'click':
                        await locator.click()
                    elif kind == 'fill':
                        await locator.fill(action['text'])
                    elif kind == 'press':
                        await locator.press(action['key'])
                    elif kind == 'select':
                        await locator.select_option(value=action['value'])
                    elif kind == 'check':
                        await locator.set_checked(action['checked'])
                    elif kind == 'reload':
                        await page.reload(wait_until='load', timeout=timeout)
                    elif kind == 'viewport':
                        await page.set_viewport_size({'width': action['width'], 'height': action['height']})
                    elif kind == 'inspect':
                        row['observation'] = await locator.evaluate_all(_ELEMENTS)
                    elif kind == 'screenshot':
                        name = f'step-{index:04d}.png'
                        await page.screenshot(path=str(output / name), full_page=True, timeout=timeout)
                        row['screenshot'] = name
                    elif kind.startswith('expect_'):
                        assertion = expect(locator)
                        if kind == 'expect_text':
                            await assertion.to_have_text(action['text'], timeout=timeout)
                        elif kind == 'expect_count':
                            await assertion.to_have_count(action['count'], timeout=timeout)
                        elif kind == 'expect_visible':
                            await (assertion.to_be_visible if action['visible'] else assertion.to_be_hidden)(timeout=timeout)
                        elif kind == 'expect_checked':
                            await assertion.to_be_checked(checked=action['checked'], timeout=timeout)
                        else:
                            raise ValueError('unknown browser assertion')
                        result['assertions_passed'] += 1
                    else:
                        raise ValueError('unknown browser action')
                    row['status'] = 'passed'
                except Exception as error:
                    row.update(status='failed', error=str(error))
                    raise
                finally:
                    save()
            result['status'] = 'passed'
        except Exception as error:
            result.update(status='failed', error=f'{type(error).__name__}: {error}')
        finally:
            save()
            if page is not None and not page.is_closed():
                try:
                    result['snapshot'] = {
                        'url': page.url, 'title': await page.title(), 'viewport': page.viewport_size,
                        'body_text': await page.locator('body').inner_text(timeout=remaining_ms()),
                        'layout': await page.evaluate('({width:innerWidth,scrollWidth:document.documentElement.scrollWidth})'),
                        'controls': await page.locator('input,button,a,select,textarea').evaluate_all(_ELEMENTS)}
                    await page.screenshot(path=str(output / 'final.png'), full_page=True, timeout=remaining_ms())
                except Exception as error:
                    result['snapshot_error'] = str(error)
            if context is not None:
                try:
                    await context.tracing.stop(path=str(output / 'trace.zip'))
                    await context.close()
                except Exception as error:
                    result['close_error'] = str(error)
            if browser is not None:
                await browser.close()
            save()
    return result


if __name__ == '__main__':
    specification = json.loads(Path(sys.argv[1]).read_text())
    record = asyncio.run(run_browser(specification, Path(sys.argv[2])))
    print(json.dumps({'status': record['status'], 'assertions_passed': record['assertions_passed'],
                      'error': record['error']}, ensure_ascii=False))
    raise SystemExit(0 if record['status'] == 'passed' else 1)
