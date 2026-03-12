import { IProfileForm } from '@Entities/users/models/profile-form.dto.ts';

export interface IInviteUserDto extends IProfileForm {
    language: string
}
