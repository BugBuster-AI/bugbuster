import { BaseFlex } from '@Components/BaseLayout';
import { Search } from '@Components/Seach';
import { useAuthStore } from '@Entities/auth/store/auth.store.ts';
import { EUserRole } from '@Entities/users/models';
import { InviteUser } from '@Features/users/invite-user';

export const UsersToolbar = () => {
    // const { t } = useTranslation()
    const user = useAuthStore((state) => state.user)

    return (
        <BaseFlex gap={ 8 }>
            {user?.role === EUserRole.ADMIN ? <InviteUser/> : null}

            <Search/>

            {/*<Button type={ 'link' }>{t('users.filter')}</Button>*/}
        </BaseFlex>
    )
}
