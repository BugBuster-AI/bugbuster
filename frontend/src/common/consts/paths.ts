export const PATHS = {
    INDEX: '/',

    WORKSPACE: {
        INDEX: '/',
        ABSOLUTE: '/',

        USERS: {
            INDEX: 'users',
            ABSOLUTE: `/users`
        },

        LOGS: {
            INDEX: 'logs',
            ABSOLUTE: '/logs'
        },

        API_KEYS: {
            INDEX: 'api-keys',
            ABSOLUTE: '/api-keys'
        },

        BILLING: {
            INDEX: 'billing',
            ABSOLUTE: '/billing'
        }
    },


    PROJECT: {
        INDEX: 'project',
        ABSOLUTE: (id: string) => `/project/${id}`
    },

    AUTH: {
        INDEX: 'auth',
        ABSOLUTE: '/auth',

        LOGIN: {
            INDEX: 'login',
            ABSOLUTE: '/auth/login'
        },

        GOOGLE: {
            INDEX: 'google',
            ABSOLUTE: '/auth/google'
        },

        SIGNUP: {
            INDEX: 'signup',
            ABSOLUTE: '/auth/signup'
        },

        RESET_PASS: {
            INDEX: 'reset',
            ABSOLUTE: '/auth/reset'
        },

        CONFIRM_RESET: {
            INDEX: 'reset-password',
            ABSOLUTE: '/reset-password'
        }
    },

    REPOSITORY: {
        INDEX: 'repository',
        ABSOLUTE: (id: string) => `/project/${id}/repository`,

        CREATE_CASE: {
            INDEX: 'create-case',
            ABSOLUTE: (id: string) => `${PATHS.REPOSITORY.ABSOLUTE(id)}/create-case`
        },

        EDIT_CASE: {
            ABSOLUTE: (id: string, caseId: string) => `${PATHS.REPOSITORY.ABSOLUTE(id)}/edit/${caseId}`
        }
    },

    RUNS: {
        INDEX: 'runs',
        ABSOLUTE: (id: string) => `/project/${id}/runs`
    },

    RECORDS: {
        INDEX: 'records',
        ABSOLUTE: (id: string) => `/project/${id}/records`
    },

    PLANS: {
        INDEX: 'plans',
        ABSOLUTE: (id: string) => `/project/${id}/plans`
    },

    ENVIRONMENTS: {
        INDEX: 'environments',
        ABSOLUTE: (id: string) => `/project/${id}/environments`
    },

    RUNNING: {
        ABSOLUTE: (id: string) => `/running/${id}`
    },

    VARIABLES: {
        INDEX: 'variables',
        ABSOLUTE: (projectId: string) => `/project/${projectId}/variables`
    },

    SHARED_STEPS: {
        INDEX: 'shared_steps',
        ABSOLUTE: (projectId: string) => `/project/${projectId}/shared_steps`
    }
};
