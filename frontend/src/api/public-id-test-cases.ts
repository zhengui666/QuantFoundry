import { PublicIdExamples, PublicIdSchemas, type PublicIdType } from './generated/runtime-schemas';

export type PublicIdNegativeCase = Readonly<{
  caseId:
    | 'QF-PID-003'
    | 'QF-PID-004'
    | 'QF-PID-005'
    | 'QF-PID-006'
    | 'QF-PID-007'
    | 'QF-PID-008'
    | 'QF-PID-009'
    | 'QF-PID-010'
    | 'QF-PID-011';
  mutation: string;
  value: string;
}>;

const publicIdTypes = Object.keys(PublicIdSchemas) as PublicIdType[];

const replaceUuidNibble = (value: string, index: number, nibble: string): string => {
  const separator = value.indexOf('-');
  const prefix = value.slice(0, separator);
  const compact = value
    .slice(separator + 1)
    .replaceAll('-', '')
    .split('');
  compact[index] = nibble;
  return `${prefix}-${compact.slice(0, 8).join('')}-${compact.slice(8, 12).join('')}-${compact.slice(12, 16).join('')}-${compact.slice(16, 20).join('')}-${compact.slice(20).join('')}`;
};

const mutateUlidCharacter = (value: string, index: number, character: string): string => {
  const separator = value.indexOf('-');
  const prefix = value.slice(0, separator);
  const suffix = value.slice(separator + 1).split('');
  suffix[index] = character;
  return `${prefix}-${suffix.join('')}`;
};

const mixedCaseUuid = (value: string): string => {
  const separator = value.indexOf('-');
  const prefix = value.slice(0, separator + 1);
  const suffix = value.slice(separator + 1);
  const alphabeticIndex = [...suffix].findIndex((character) => /[a-f]/.test(character));
  return `${prefix}${suffix.slice(0, alphabeticIndex)}${suffix[alphabeticIndex]?.toUpperCase()}${suffix.slice(alphabeticIndex + 1)}`;
};

export const canonicalPublicIdForms = (type: PublicIdType): readonly [string, string] => [
  PublicIdExamples[type].ulid,
  PublicIdExamples[type].uuid,
];

export const publicIdNegativeCases = (type: PublicIdType): readonly PublicIdNegativeCase[] => {
  const { ulid, uuid } = PublicIdExamples[type];
  const prefix = ulid.slice(0, ulid.indexOf('-'));
  const nextType = publicIdTypes[(publicIdTypes.indexOf(type) + 1) % publicIdTypes.length];
  if (!nextType) throw new Error(`No generated public-ID rotation target for ${type}`);
  const wrongPrefix = PublicIdExamples[nextType].ulid;

  return [
    { caseId: 'QF-PID-003', mutation: 'empty suffix', value: `${prefix}-` },
    { caseId: 'QF-PID-003', mutation: 'short suffix', value: `${prefix}-1` },
    { caseId: 'QF-PID-004', mutation: 'wrong generated prefix', value: wrongPrefix },
    { caseId: 'QF-PID-005', mutation: 'lowercase ULID', value: ulid.toLowerCase() },
    ...(['I', 'L', 'O', 'U'] as const).map((character) => ({
      caseId: 'QF-PID-005' as const,
      mutation: `illegal Crockford ${character}`,
      value: mutateUlidCharacter(ulid, 1, character),
    })),
    ...(['8', '9', 'Z'] as const).map((character) => ({
      caseId: 'QF-PID-006' as const,
      mutation: `ULID overflow ${character}`,
      value: mutateUlidCharacter(ulid, 0, character),
    })),
    { caseId: 'QF-PID-007', mutation: 'uppercase UUID', value: uuid.toUpperCase() },
    { caseId: 'QF-PID-007', mutation: 'mixed-case UUID', value: mixedCaseUuid(uuid) },
    ...(['1', '3', '5'] as const).map((nibble) => ({
      caseId: 'QF-PID-008' as const,
      mutation: `UUID version ${nibble}`,
      value: replaceUuidNibble(uuid, 12, nibble),
    })),
    ...(['0', '7', 'c', 'f'] as const).map((nibble) => ({
      caseId: 'QF-PID-009' as const,
      mutation: `UUID variant ${nibble}`,
      value: replaceUuidNibble(uuid, 16, nibble),
    })),
    { caseId: 'QF-PID-010', mutation: 'single suffix character', value: `${ulid}X` },
    { caseId: 'QF-PID-010', mutation: 'second suffix', value: `${ulid}-EXTRA` },
    { caseId: 'QF-PID-010', mutation: 'leading space', value: ` ${ulid}` },
    { caseId: 'QF-PID-010', mutation: 'trailing space', value: `${ulid} ` },
    { caseId: 'QF-PID-010', mutation: 'leading newline', value: `\n${ulid}` },
    { caseId: 'QF-PID-010', mutation: 'trailing newline', value: `${ulid}\n` },
    ...(type === 'memo'
      ? [
          {
            caseId: 'QF-PID-011' as const,
            mutation: 'legacy Memo prefix',
            // reject_fixture: constructed from the generated MEMO fixture; no alias is accepted.
            value: ulid.replace(/^MEMO-/, 'MEM-'),
          },
        ]
      : []),
  ];
};

export const publicIdRouteCases = [
  { path: 'research', type: 'research' },
  { path: 'experiments', type: 'experiment' },
  { path: 'strategies', type: 'strategy' },
  { path: 'validation', type: 'validation' },
  { path: 'approvals', type: 'approval' },
  { path: 'memos', type: 'memo' },
] as const satisfies readonly { path: string; type: PublicIdType }[];
