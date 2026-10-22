<?php

declare(strict_types=1);

function respond(array $payload, int $status = 200): never
{
    if (PHP_SAPI !== 'cli') {
        http_response_code($status);
        header('Content-Type: application/json');
    }
    echo json_encode($payload, JSON_UNESCAPED_SLASHES), PHP_SAPI === 'cli' ? PHP_EOL : '';
    exit($status === 200 ? 0 : 1);
}

function case_name(): string
{
    if (PHP_SAPI === 'cli') {
        global $argv;

        return $argv[1] ?? 'health';
    }

    $case = $_GET['case'] ?? 'health';

    return is_string($case) ? $case : 'health';
}

function flag_path(): string
{
    $path = getenv('OOM_FLAG');

    return is_string($path) && $path !== '' ? $path : '/tmp/oom-shutdown';
}

function normal_payload(): array
{
    $packed = serialize(['a' => 1, 'b' => ['c', 'd']]);
    $xml = simplexml_load_string('<root><item>hi</item></root>');
    $file = tempnam(sys_get_temp_dir(), 'php');
    file_put_contents($file, 'hello');
    $got = file_get_contents($file);
    unlink($file);

    $fiber = new Fiber(static function (): int {
        return 7;
    });
    $yielded = [];
    foreach ((static function () {
        yield 1;
        yield 2;
    })() as $n) {
        $yielded[] = $n;
    }

    return [
        'explode' => explode(',', 'a,b,c'),
        'replace' => str_replace('a', 'b', 'ababa'),
        'chunks' => str_split('abcdef', 2),
        'csv' => str_getcsv('a,b,"c,d"'),
        'fill' => array_fill(0, 3, 'x'),
        'range' => range(1, 3),
        'json' => json_decode('{"n":1,"s":"ok"}', true),
        'encoded' => json_encode(['n' => 1, 's' => 'ok']),
        'unserialize' => unserialize($packed, ['allowed_classes' => false]),
        'preg' => preg_match('/^t.+s$/', 'timur-images') === 1,
        'mb_strlen' => function_exists('mb_strlen') ? mb_strlen('timur') : null,
        'hash' => hash('sha256', 'timur-images'),
        'pbkdf2' => hash_pbkdf2('sha256', 'pass', 'salt', 1, 16),
        'gz' => gzdecode(gzencode('timur-images')),
        'xml' => (string) $xml->item,
        'file' => $got,
        'fiber' => $fiber->start(),
        'generator' => $yielded,
        'curl' => function_exists('curl_version') ? curl_version()['version'] : null,
    ];
}

function exhaust_soft(int $capBytes): void
{
    if (ini_set('memory_limit', '8M') === false) {
        respond(['ok' => false, 'error' => 'ini_set memory_limit failed'], 500);
    }

    $buf = '';
    $bytes = 0;
    while ($bytes < $capBytes) {
        $buf .= str_repeat('x', 32768);
        $bytes += 32768;
    }
    unset($buf);
}

function case_oom_soft(): void
{
    $flag = flag_path();
    @unlink($flag);
    $flagHandle = fopen($flag, 'c');
    $handlerCalls = 0;
    $finally = false;
    $caught = false;
    $type = null;
    $message = 'memory limit was not reached';
    set_error_handler(static function () use (&$handlerCalls): bool {
        $handlerCalls++;

        return true;
    });
    register_shutdown_function(static function () use ($flagHandle): void {
        fwrite($flagHandle, '1');
    });

    try {
        try {
            exhaust_soft(12 * 1024 * 1024);
        } catch (Throwable $e) {
            $caught = true;
            $type = $e::class;
            $message = $e->getMessage();
        } finally {
            $finally = true;
        }
    } catch (Throwable $e) {
        $caught = true;
        $type = $e::class;
        $message = $e->getMessage();
    }

    ini_set('memory_limit', '256M');
    $last = error_get_last();
    respond([
        'ok' => $caught && $finally,
        'caught' => $caught,
        'finally' => $finally,
        'type' => $type,
        'message' => $message,
        'handler_calls' => $handlerCalls,
        'error_get_last' => $last,
        'hard_limit' => ini_get('memory_hard_limit_percent'),
    ], ($caught && $finally) ? 200 : 500);
}

function case_oom_hard(): void
{
    $flag = flag_path();
    @unlink($flag);
    $flagHandle = fopen($flag, 'c');
    register_shutdown_function(static function () use ($flagHandle): void {
        fwrite($flagHandle, '1');
    });
    fwrite(STDERR, "before-hard-oom\n");
    str_repeat('x', 96 * 1024 * 1024);
    fwrite(STDERR, "after-hard-oom\n");
    respond(['ok' => false, 'error' => 'hard allocation returned']);
}

function case_oom_ob(): void
{
    ini_set('memory_limit', '8M');
    ob_start(static function (string $buffer): string {
        $block = '';
        $bytes = 0;
        try {
            while ($bytes < 12 * 1024 * 1024) {
                $block .= str_repeat('y', 32768);
                $bytes += 32768;
            }
        } catch (Throwable) {
            ini_set('memory_limit', '256M');

            return 'from-handler';
        }
        unset($block);

        return $buffer;
    });
    echo 'page-body';
    $output = ob_get_clean();
    ini_set('memory_limit', '256M');
    respond([
        'ok' => true,
        'output' => $output,
    ]);
}

function case_pbkdf2_huge(): void
{
    fwrite(STDERR, "before-pbkdf2\n");
    hash_pbkdf2('sha256', 'pass', 'salt', 1, 96 * 1024 * 1024);
    fwrite(STDERR, "after-pbkdf2\n");
    respond(['ok' => false, 'error' => 'hash_pbkdf2 returned']);
}

function nesting_depth(mixed $value): int
{
    if (!is_array($value)) {
        return 0;
    }
    $max = 0;
    foreach ($value as $item) {
        $child = 1 + nesting_depth($item);
        if ($child > $max) {
            $max = $child;
        }
    }

    return $max;
}

function case_post(): void
{
    $started = @session_start();
    $files = [];
    foreach ($_FILES as $name => $info) {
        $files[$name] = [
            'error' => $info['error'] ?? null,
            'size' => $info['size'] ?? null,
            'name' => $info['name'] ?? null,
            'full_path' => $info['full_path'] ?? null,
        ];
    }
    respond([
        'ok' => true,
        'post_count' => count($_POST, COUNT_RECURSIVE),
        'top_keys' => array_keys($_POST),
        'depth' => nesting_depth($_POST),
        'files' => $files,
        'raw_len' => strlen((string) file_get_contents('php://input')),
        'session_started' => $started,
        'session' => $_SESSION ?? null,
        'content_length' => $_SERVER['CONTENT_LENGTH'] ?? null,
        'content_type' => $_SERVER['CONTENT_TYPE'] ?? null,
    ]);
}

function case_parse_body(): void
{
    try {
        [$post, $files] = request_parse_body(['post_max_size' => '1K']);
        respond([
            'ok' => true,
            'post' => $post,
            'file_keys' => array_keys($files),
        ]);
    } catch (Throwable $e) {
        respond([
            'ok' => false,
            'error' => $e::class,
            'message' => $e->getMessage(),
        ], 500);
    }
}

function case_oom_json(): void
{
    ini_set('memory_limit', '8M');
    try {
        $raw = '[' . str_repeat('1,', 2000000) . '1]';
        $decoded = json_decode($raw, true);
        unset($raw);
        ini_set('memory_limit', '256M');
        respond([
            'ok' => true,
            'exhausted' => false,
            'count' => is_array($decoded) ? count($decoded) : null,
        ]);
    } catch (Throwable $e) {
        ini_set('memory_limit', '256M');
        respond([
            'ok' => true,
            'exhausted' => true,
            'type' => $e::class,
            'message' => $e->getMessage(),
        ]);
    }
}

$case = case_name();

switch ($case) {
    case 'health':
        respond([
            'ok' => true,
            'sapi' => PHP_SAPI,
            'version' => PHP_VERSION,
            'memory_limit' => ini_get('memory_limit'),
            'memory_hard_limit_percent' => ini_get('memory_hard_limit_percent'),
            'extensions' => [
                'json' => extension_loaded('json'),
                'session' => extension_loaded('session'),
                'mbstring' => extension_loaded('mbstring'),
                'curl' => extension_loaded('curl'),
                'zlib' => extension_loaded('zlib'),
                'simplexml' => extension_loaded('simplexml'),
                'gd' => extension_loaded('gd'),
                'exif' => extension_loaded('exif'),
                'soap' => extension_loaded('soap'),
            ],
        ]);
    case 'normal':
        respond(['ok' => true, 'result' => normal_payload()]);
    case 'oom-soft':
        case_oom_soft();
    case 'oom-hard':
        case_oom_hard();
    case 'oom-ob':
        case_oom_ob();
    case 'pbkdf2-huge':
        case_pbkdf2_huge();
    case 'post':
        case_post();
    case 'parse-body':
        case_parse_body();
    case 'oom-json':
        case_oom_json();
    default:
        respond(['ok' => false, 'error' => 'unknown case', 'case' => $case], 404);
}
