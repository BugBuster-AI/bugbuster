export interface IStreamStat {
    active_streams: number,
    total_streams: number
}

export interface IStreamsStatList {
    workspace_statistics: IStreamStat
    project_statistics: Record<string, IStreamStat>,
    group_run_statistics: Record<string, IStreamStat>
}
