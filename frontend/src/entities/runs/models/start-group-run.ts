export interface IStartGroupRunDto {
    group_run_id: string;
    run_automated?: boolean
    run_manual?: boolean
    runIds?: string[]
}
