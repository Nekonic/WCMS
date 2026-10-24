import type { components } from './schema';

type Schemas = components['schemas'];

export type LivePC = Schemas['LivePC'];
export type PublicSeat = Schemas['PublicSeat'];
export type PublicRoom = Schemas['PublicRoom'];
export type Room = Schemas['Room'];
export type PC = Schemas['PC'];
export type Pin = Schemas['Pin'];
export type Admin = Schemas['Admin'];
export type Me = Schemas['Me'];
export type AuditLog = Schemas['AuditLog'];
export type EnrollInfo = Schemas['EnrollInfo'];
export type ApiErrorBody = Schemas['Error'];
