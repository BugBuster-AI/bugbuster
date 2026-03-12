import { IMedia } from '@Entities/runs/models';
import { IActionPlan } from '@Entities/test-case/models';

export interface IRecordListItem {
    name: string;
    id: string;
    date: string;
    context: string;
    createdBy: string
}

export interface IHappyPassListItem {
    happy_pass_id: string;
    created_at: string;
    action_plan: IActionPlan[]
    steps: string[],
    name: string;
    context: string
}

export interface IGetHappypassPayload {
    happy_pass_id?: string;
    name?: string
    project_id: string
    context?: string;
    limit?: string;
    offset?: string
}

export interface IFullDataStep {
    id: string;
    action: string;
    timestamp: string;
    beforeScreenshot: IMedia
    beforeAnnotatedScreenshot: IMedia;
    elementDetails: {
        windowWidth: number;
        windowHeight: number;
        url: string;
        elementType: string;
        elementId: string;
        elementText: string;
        elementClass: string;
        elementOuterHTML: string;
        parentElementType: string
        parentElementId: string;
        parentElementClass: string
        parentElementOuterHTML: string
    }
    inputText: string | null
    coords: {
        x: number;
        y: number;
    }
    recording_name: string
}

export interface IFullDataHappypass {
    user_id: string;
    task_id: string
    recording_name: string;
    context: string;
    steps: IFullDataStep[]
}

export interface IFullHappyPastListItem extends IHappyPassListItem {
    full_data: IFullDataHappypass
    images: IMedia[]
}

// Интерфейс данных GET/records/happypass
export interface IFullHappypass {
    total: number,
    total_current_page: number,
    page: number,
    size: number,
    pages: number,
    limit: number,
    offset: number,
    items: IFullHappyPastListItem[]
}
