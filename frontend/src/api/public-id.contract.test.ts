import { describe, expect, it } from 'vitest';
import { auth, parsePublicId, workspaceQueryKey } from './client';
import {
  AnyPublicSemanticIdSchema,
  ObjectRefSchema,
  PublicIdExamples,
  PublicIdSchemas,
  type PublicIdType,
  VersionRefSchema,
} from './generated/runtime-schemas';

const entries = Object.entries(PublicIdExamples) as Array<
  [PublicIdType, { readonly ulid: string; readonly uuid: string }]
>;
const positiveCases = entries.flatMap(([type, examples]) =>
  ([examples.ulid, examples.uuid] as const).map((value) => [type, value] as const),
);
const prefixOf = (value: string) => value.slice(0, value.indexOf('-'));
const replaceUuidNibble = (value: string, compactIndex: number, nibble: string): string => {
  const [prefix, ...suffixParts] = value.split('-');
  const suffix = suffixParts.join('-');
  const hyphenless = suffix.replaceAll('-', '');
  const changed = `${hyphenless.slice(0, compactIndex)}${nibble}${hyphenless.slice(compactIndex + 1)}`;
  return `${prefix}-${changed.slice(0, 8)}-${changed.slice(8, 12)}-${changed.slice(12, 16)}-${changed.slice(16, 20)}-${changed.slice(20)}`;
};

describe('QF-PID generated public semantic ID contract', () => {
  it('QF-PID bootstrap keeps exactly 34 generated classes', () => {
    expect(entries).toHaveLength(34);
    expect(Object.keys(PublicIdSchemas)).toEqual(Object.keys(PublicIdExamples));
  });

  it.each(positiveCases)('QF-PID-001/002 accepts %s positive %s byte-exact', (type, value) => {
    expect(PublicIdSchemas[type].parse(value)).toBe(value);
    expect(AnyPublicSemanticIdSchema.parse(value)).toBe(value);
    expect(parsePublicId(type, value)).toBe(value);
  });

  it('QF-PID-003 rejects empty and short suffixes for all 34 classes', () => {
    for (const [type, { ulid }] of entries) {
      const prefix = prefixOf(ulid);
      for (const value of [`${prefix}-`, `${prefix}-1`])
        expect(PublicIdSchemas[type].safeParse(value).success).toBe(false);
    }
  });

  it('QF-PID-004 rejects the next generated prefix for all 34 classes', () => {
    for (const [index, [type]] of entries.entries()) {
      const wrong = entries[(index + 1) % entries.length]![1].ulid;
      expect(PublicIdSchemas[type].safeParse(wrong).success).toBe(false);
    }
  });

  it('QF-PID-005 rejects lowercase and each illegal Crockford glyph', () => {
    for (const [type, { ulid }] of entries) {
      const prefix = prefixOf(ulid);
      const suffix = ulid.slice(prefix.length + 1);
      expect(PublicIdSchemas[type].safeParse(`${prefix}-${suffix.toLowerCase()}`).success).toBe(
        false,
      );
      for (const glyph of ['I', 'L', 'O', 'U'])
        expect(
          PublicIdSchemas[type].safeParse(
            `${prefix}-${suffix.slice(0, 1)}${glyph}${suffix.slice(2)}`,
          ).success,
        ).toBe(false);
    }
  });

  it('QF-PID-006 rejects every overflowing ULID first glyph', () => {
    for (const [type, { ulid }] of entries) {
      const prefix = prefixOf(ulid);
      const suffix = ulid.slice(prefix.length + 1);
      for (const glyph of ['8', '9', 'Z'])
        expect(
          PublicIdSchemas[type].safeParse(`${prefix}-${glyph}${suffix.slice(1)}`).success,
        ).toBe(false);
    }
  });

  it('QF-PID-007 rejects uppercase and mixed-case UUIDs without normalization', () => {
    for (const [type, { uuid }] of entries) {
      const prefix = prefixOf(uuid);
      const suffix = uuid.slice(prefix.length + 1);
      for (const value of [suffix.toUpperCase(), suffix.replace('e', 'E')])
        expect(PublicIdSchemas[type].safeParse(`${prefix}-${value}`).success).toBe(false);
    }
  });

  it('QF-PID-008 rejects all specified non-v4 UUID version nibbles', () => {
    for (const [type, { uuid }] of entries)
      for (const nibble of ['1', '3', '5'])
        expect(PublicIdSchemas[type].safeParse(replaceUuidNibble(uuid, 12, nibble)).success).toBe(
          false,
        );
  });

  it('QF-PID-009 rejects all specified invalid UUID variant nibbles', () => {
    for (const [type, { uuid }] of entries)
      for (const nibble of ['0', '7', 'c', 'f'])
        expect(PublicIdSchemas[type].safeParse(replaceUuidNibble(uuid, 16, nibble)).success).toBe(
          false,
        );
  });

  it('QF-PID-010 rejects suffixes, whitespace, and newlines without trim/truncation', () => {
    for (const [type, { ulid }] of entries)
      for (const value of [
        `${ulid}X`,
        `${ulid}-EXTRA`,
        ` ${ulid}`,
        `${ulid} `,
        `\n${ulid}`,
        `${ulid}\n`,
      ])
        expect(PublicIdSchemas[type].safeParse(value).success).toBe(false);
  });

  it('QF-PID-011 rejects legacy MEM while accepting both exact MEMO forms', () => {
    // reject_fixture MEM-01ARZ3NDEKTSV4RRFFQ69G5FAV
    expect(AnyPublicSemanticIdSchema.safeParse('MEM-01ARZ3NDEKTSV4RRFFQ69G5FAV').success).toBe(
      false,
    );
    expect(PublicIdSchemas.memo.parse(PublicIdExamples.memo.ulid)).toBe(PublicIdExamples.memo.ulid);
    expect(PublicIdSchemas.memo.parse(PublicIdExamples.memo.uuid)).toBe(PublicIdExamples.memo.uuid);
  });

  it('QF-PID-012 accepts 34 own-prefix refs and rejects all 34×33 mismatches', () => {
    let mismatches = 0;
    for (const [type, { ulid }] of entries) {
      const own = { type, id: ulid, version: null, revision: 1 };
      expect(ObjectRefSchema.safeParse(own).success).toBe(true);
      for (const [wrongType] of entries) {
        if (wrongType === type) continue;
        mismatches += 1;
        expect(ObjectRefSchema.safeParse({ ...own, type: wrongType }).success).toBe(false);
      }
    }
    expect(mismatches).toBe(34 * 33);
    expect(
      ObjectRefSchema.safeParse({
        type: 'unknown',
        id: PublicIdExamples.research.ulid,
        version: null,
        revision: 1,
      }).success,
    ).toBe(false);
  });

  it('QF-PID-012 keeps VersionRef limited to exact Factor/Strategy IDs', () => {
    for (const id of [PublicIdExamples.factor.ulid, PublicIdExamples.strategy.uuid])
      expect(VersionRefSchema.parse({ id, version: 1 })).toEqual({ id, version: 1 });
    expect(
      VersionRefSchema.safeParse({ id: PublicIdExamples.research.ulid, version: 1 }).success,
    ).toBe(false);
  });

  it('QF-PID-013 preserves the exact 42-byte DSSET UUID through URL/cache/ObjectRef round-trip', () => {
    const id = PublicIdExamples.dataset.uuid;
    expect(id).toHaveLength(42);
    const validatedId = parsePublicId('dataset', id);
    const cacheKey = workspaceQueryKey('dataset', validatedId);
    expect(cacheKey[2]).toBe(id);
    const routed = decodeURIComponent(encodeURIComponent(validatedId));
    expect(routed).toBe(id);
    expect(
      ObjectRefSchema.parse({ type: 'dataset', id: routed, version: null, revision: 1 }).id,
    ).toBe(id);
    expect(PublicIdSchemas.dataset.safeParse(id.slice(0, 40)).success).toBe(false);
  });

  it('QF-PID-013 keeps exact IDs behind opaque rotating workspace cache scope', () => {
    const id = PublicIdExamples.experiment.ulid;
    const before = workspaceQueryKey('experiment', id);
    auth.set('bearer-A');
    const first = workspaceQueryKey('experiment', id);
    auth.set('bearer-B');
    const second = workspaceQueryKey('experiment', id);
    expect(new Set([before[0], first[0], second[0]])).toHaveLength(3);
    expect(first.slice(1)).toEqual(['experiment', id]);
    expect(second.slice(1)).toEqual(['experiment', id]);
    expect(JSON.stringify([first, second])).not.toContain('bearer-');
    auth.clear();
  });
});
