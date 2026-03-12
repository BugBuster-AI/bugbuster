// HINT: функция для поддержки старого формата
import { EStepType } from '@Entities/test-case/components/Form/models.ts';

// notExpected - в ранах expected - значит что шага есть проверки, поэтому надо прокидывать этот параметр
export const convertStepType
    = (type?: EStepType | 'expected' | 'api' | undefined, notExpected?: boolean): EStepType | undefined => {

        switch (type) {
            case 'expected':
                if (notExpected) {
                    return EStepType.STEP
                }

                return EStepType.RESULT;
            case 'api':
                return EStepType.API
            default:
                return type
        }
    }
