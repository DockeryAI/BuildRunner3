import { beforeEach, describe, expect, it } from 'vitest';

import { normalizeBuildSession, useBuildStore } from './buildStore';


describe('buildStore runtime metadata', () => {
  beforeEach(() => {
    useBuildStore.getState().resetStore();
  });

  it('stores runtime-aware session metadata', () => {
    useBuildStore.getState().setSession({
      id: 'session-1',
      projectName: 'BuildRunner3',
      projectAlias: 'br3',
      projectPath: '/tmp/br3',
      startTime: Date.now(),
      status: 'running',
      components: [],
      features: [],
      runtime: 'codex',
      backend: 'codex-cli 0.48.0',
      runtimeSource: 'explicit',
      runtimeSessionId: 'thread-123',
      capabilities: { review: true },
      dispatchMode: 'parallel_shadow',
      shadowRuntime: 'codex',
      shadowStatus: 'shadow_completed',
    });

    const session = useBuildStore.getState().session;

    expect(session?.runtime).toBe('codex');
    expect(session?.backend).toBe('codex-cli 0.48.0');
    expect(session?.dispatchMode).toBe('parallel_shadow');
    expect(session?.shadowStatus).toBe('shadow_completed');
  });

  it('normalizes snake_case API payloads into the store shape', () => {
    const normalized = normalizeBuildSession({
      id: 'session-2',
      project_name: 'BuildRunner3',
      project_alias: 'br3',
      project_path: '/tmp/br3',
      start_time: 123,
      status: 'running',
      components: [],
      features: [],
      runtime: 'codex',
      runtime_source: 'explicit',
      runtime_session_id: 'thread-123',
      dispatch_mode: 'parallel_shadow',
      shadow_runtime: 'codex',
      shadow_status: 'shadow_completed',
    });

    expect(normalized.projectName).toBe('BuildRunner3');
    expect(normalized.projectAlias).toBe('br3');
    expect(normalized.runtimeSource).toBe('explicit');
    expect(normalized.dispatchMode).toBe('parallel_shadow');
    expect(normalized.shadowStatus).toBe('shadow_completed');
  });

  it('patches runtime metadata without relying on stale session closures', () => {
    useBuildStore.getState().setSession({
      id: 'session-3',
      projectName: 'BuildRunner3',
      projectAlias: 'br3',
      projectPath: '/tmp/br3',
      startTime: Date.now(),
      status: 'running',
      components: [],
      features: [],
      runtime: 'claude',
    });

    useBuildStore.getState().patchSession({
      runtime: 'codex',
      runtime_source: 'explicit',
      dispatch_mode: 'parallel_shadow',
    });

    const session = useBuildStore.getState().session;
    expect(session?.runtime).toBe('codex');
    expect(session?.runtimeSource).toBe('explicit');
    expect(session?.dispatchMode).toBe('parallel_shadow');
  });

  it('ignores malformed capabilities payloads from websocket updates', () => {
    useBuildStore.getState().setSession({
      id: 'session-4',
      projectName: 'BuildRunner3',
      projectAlias: 'br3',
      projectPath: '/tmp/br3',
      startTime: Date.now(),
      status: 'running',
      components: [],
      features: [],
      runtime: 'claude',
      capabilities: { review: true },
    });

    useBuildStore.getState().patchSession({
      capabilities: ['not', 'an', 'object'],
    } as unknown as Record<string, unknown>);

    const session = useBuildStore.getState().session;
    expect(session?.capabilities).toEqual({ review: true });
  });
});
