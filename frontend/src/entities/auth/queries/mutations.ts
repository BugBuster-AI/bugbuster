import { AuthApi } from '@Entities/auth/api';
import { useMutation } from '@tanstack/react-query';

const authApi = AuthApi.getInstance()

export const useFastSignup = () => {

    return useMutation({
        mutationFn: (email: string) => authApi.fastSignup(email),
    })
}
