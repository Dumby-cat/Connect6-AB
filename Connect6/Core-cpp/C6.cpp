#include <iostream>
#include <vector>
#include <algorithm>
#include <chrono>

using namespace std;

#define GRID_SIZE 9 // 棋盘大小
#define EMPTY_CELL 0 // 空格标志
#define BLACK_PIECE 1 // 黑棋标志
#define WHITE_PIECE (-1) // 白棋标志

const int INFINITY_VALUE = numeric_limits<int>::max() - 1; // 无穷大

// 设置搜索最长时间为 2 秒
const int MAX_SEARCH_TIME_MS = 2000; // 单位：毫秒

// 记录搜索开始时间
auto search_start_time = chrono::high_resolution_clock::now();

// 判断是否超时
bool IsTimeUp() {
    auto current_time = chrono::high_resolution_clock::now();
    auto elapsed_time = chrono::duration_cast<chrono::milliseconds>(current_time - search_start_time).count();
    return elapsed_time >= MAX_SEARCH_TIME_MS;
}

// 棋盘边界
int top_boundary = GRID_SIZE; // 上边界
int bottom_boundary = 0; // 下边界
int left_boundary = GRID_SIZE; // 左边界
int right_boundary = 0; // 右边界

int bot_color; // 当前机器人执棋颜色（1为黑，-1为白）
int board_state[GRID_SIZE][GRID_SIZE] = { 0 }; // 棋盘状态，先x后y

// 棋步结构体
struct Move {
    int x; // 横坐标
    int y; // 纵坐标
};

// 棋步及其评分结构体
struct MoveWithScore {
    int score; // 棋步对应的评分
    Move move; // 棋步
};
vector<MoveWithScore> legal_moves; // 存储所有合法棋步
Move optimal_moves[2]; // 最终决策的两步棋
vector<Move> simulated_moves; // 模拟落子的棋步

// 判断是否在棋盘内
inline bool IsWithinBoard(int x, int y) {
    return x >= 0 && x < GRID_SIZE && y >= 0 && y < GRID_SIZE;
}

// 获取某条道的棋子
vector<int> GetLinePieces(Move move, int dx, int dy) {
    vector<int> line;
    for (int i = -5; i <= 5; i++) {
        int x = move.x + i * dx, y = move.y + i * dy;
        if (IsWithinBoard(x, y)) line.push_back(board_state[x][y]);
    }
    return line;
}

// 在坐标处落子，检查模拟落子是否合法
bool PlacePiece(int x0, int y0, int x1, int y1, int piece_color, bool check_only) {
    if (x1 == -1 || y1 == -1) { // 单步落子
        if (!IsWithinBoard(x0, y0) || board_state[x0][y0] != EMPTY_CELL)
            return false;
        if (!check_only) {
            board_state[x0][y0] = piece_color;
        }
        return true;
    } else { // 双步落子
        if ((!IsWithinBoard(x0, y0)) || (!IsWithinBoard(x1, y1)))
            return false;
        if (board_state[x0][y0] != EMPTY_CELL || board_state[x1][y1] != EMPTY_CELL)
            return false;
        if (!check_only) {
            board_state[x0][y0] = piece_color;
            board_state[x1][y1] = piece_color;
        }
        return true;
    }
}

// 初始评估函数
int EvaluateInitialMove(Move move, int player) {
    // 设置敌我双方各种路分数
    int self_scores[5] = { 20, 45, 50, 1000000, 1000000 };
    int opponent_scores[5] = { 1, 15, 30, 900000, 900000 };

    // 计算某条道的分值
    auto CalculateLineScore = [&](vector<int>& line) {
        int score = 0, num = (int)line.size();
        while (num < 6) line.push_back(2), num++;
        for (int i = 0; i <= num - 6; i++) {
            int self_count = 0, opponent_count = 0;
            for (int j = i; j < i + 6; j++) {
                if (line[j] == player) self_count++;
                else if (line[j] == -player) opponent_count++;
            }
            if (self_count && !opponent_count) score += self_scores[self_count - 1];
            if (!self_count && opponent_count) score += opponent_scores[opponent_count - 1];
        }
        return score;
    };

    // 计算四种道的分值
    vector<int> vertical_line = GetLinePieces(move, 0, 1); // 竖道
    vector<int> horizontal_line = GetLinePieces(move, 1, 0); // 横道
    vector<int> diagonal_line1 = GetLinePieces(move, 1, 1); // 左上右下
    vector<int> diagonal_line2 = GetLinePieces(move, 1, -1); // 左下右上
    return CalculateLineScore(vertical_line) + CalculateLineScore(horizontal_line) +
           CalculateLineScore(diagonal_line1) + CalculateLineScore(diagonal_line2);
}

// 比较函数，用于排序棋步
bool CompareMoves(const MoveWithScore& a, const MoveWithScore& b) {
    return a.score > b.score;
}

// 生成所有合法棋步
void GenerateLegalMoves(int player) {
    // 遍历棋盘，将合法棋步存入legal_moves数组
    for (int y = top_boundary; y <= bottom_boundary; y++) {
        for (int x = left_boundary; x <= right_boundary; x++) {
            if (board_state[x][y] == EMPTY_CELL) {
                Move move{};
                move.x = x;
                move.y = y;
                int score = EvaluateInitialMove(move, player); // 计算初始评分
                MoveWithScore temp{};
                temp.move = move;
                temp.score = score;
                legal_moves.push_back(temp);
            }
        }
    }
    // 将合法棋步按评分由高到低排序
    sort(legal_moves.begin(), legal_moves.end(), CompareMoves);
}

// 计算某条道的分值
int CalculateLineScore(const vector<int>& line, int player) {
    int self_scores[6] = { 1, 20, 40, 2000, 2000, 100000 };
    int opponent_scores[6] = { 1, 15, 30, 150, 5000, 90000 };
    int self_pre_score = 0, self_post_score = 0; //模拟落子前后得分
    int opponent_pre_score = 0, opponent_post_score = 0;

    int num = (int)line.size();
    for (int i = 0; i <= num - 6; i++) {
        int self_count = 0, opponent_count = 0;
        for (int j = i; j < i + 6; j++) {
            if (line[j] == player) self_count++;
            else if (line[j] == -player) opponent_count++;
        }
        if (opponent_count == 0) {
            if (self_count > 0) self_post_score += self_scores[self_count - 1];
            if (self_count > 1) self_pre_score += self_scores[self_count - 2];
        } else if (self_count == 0) {
            opponent_post_score += opponent_scores[opponent_count - 1];
            if (opponent_count > 1) opponent_pre_score += opponent_scores[opponent_count - 2];
        }
    }
    return self_post_score - self_pre_score - (opponent_post_score - opponent_pre_score); //返回模拟落子后的总得分
}

// 评估函数
int EvaluateBoard(int player) {
    int total_score = 0;
    for (const auto& move : simulated_moves) {
        total_score += CalculateLineScore(GetLinePieces(move, 0, 1), player);  // 竖道
        total_score += CalculateLineScore(GetLinePieces(move, 1, 0), player);  // 横道
        total_score += CalculateLineScore(GetLinePieces(move, 1, 1), player);  // 左上右下
        total_score += CalculateLineScore(GetLinePieces(move, 1, -1), player); // 左下右上
    }
    return total_score;
}

// Alpha-Beta 剪枝算法
int AlphaBetaSearch(int alpha, int beta, int depth, int player) {
    // 超时直接返回当前已经搜索到的最优解
    if (IsTimeUp()) {
        return 0;
    }
    // 达到搜索深度，返回评估值
    if (depth == 0) {
        return EvaluateBoard(player);
    }
    // 从合法棋步中搜索
    int num_moves = (int)legal_moves.size();
    for (int i = 0; i < num_moves && i < 12; i++) {
        // 模拟第一步落子
        Move move1 = legal_moves[i].move;
        if (board_state[move1.x][move1.y] != EMPTY_CELL) {
            continue;
        }
        board_state[move1.x][move1.y] = player;
        simulated_moves.push_back(move1);
        for (int j = 0; j < num_moves && j < 12; j++) {
            // 模拟第二步落子
            Move move2 = legal_moves[j].move;
            if (board_state[move2.x][move2.y] != EMPTY_CELL) {
                continue;
            }
            board_state[move2.x][move2.y] = player;
            simulated_moves.push_back(move2);
            // 评估局面
            int score = -AlphaBetaSearch(-beta, -alpha, depth - 1, -player);
            // 撤回第二步落子
            board_state[move2.x][move2.y] = 0;
            simulated_moves.pop_back();
            // 剪枝
            if (score >= beta) {
                // 撤回第一步落子
                board_state[move1.x][move1.y] = 0;
                simulated_moves.pop_back();
                return beta;
            }
            if (score > alpha) {
                alpha = score;
                if (depth == 2) {
                    optimal_moves[0] = move1;
                    optimal_moves[1] = move2;
                }
            }
        }
        // 撤回第一步落子
        board_state[move1.x][move1.y] = 0;
        simulated_moves.pop_back();
    }
    // 返回找到的最佳分数
    return alpha;
}

int main() {
    freopen("Con6Input.txt", "r", stdin); // 重定向输入到文件
    freopen("Con6Output.txt", "w", stdout); // 重定向输出到文件
    int x0, y0, x1, y1;
    int turn_id;
    cin >> turn_id;
    bot_color = WHITE_PIECE; // 默认假设自己是白方
    // 根据输入恢复棋盘状态
    for (int i = 0; i < turn_id; i++) {
        cin >> x0 >> y0 >> x1 >> y1;
        if (x0 == -1) {
            bot_color = BLACK_PIECE; // 第一回合收到坐标是-1, -1，说明我是黑方
        }
        if (x0 >= 0) {
            PlacePiece(x0, y0, x1, y1, -bot_color, false);
            top_boundary = min(top_boundary, y0);
            bottom_boundary = max(bottom_boundary, y0);
            left_boundary = min(left_boundary, x0);
            right_boundary = max(right_boundary, x0);
            if (i != 0 || -bot_color == WHITE_PIECE) {
                top_boundary = min(top_boundary, y1);
                bottom_boundary = max(bottom_boundary, y1);
                left_boundary = min(left_boundary, x1);
                right_boundary = max(right_boundary, x1);
            }
        }
        if (i < turn_id - 1) {
            cin >> x0 >> y0 >> x1 >> y1;
            if (x0 >= 0) {
                PlacePiece(x0, y0, x1, y1, bot_color, false);
                top_boundary = min(top_boundary, y0);
                bottom_boundary = max(bottom_boundary, y0);
                left_boundary = min(left_boundary, x0);
                right_boundary = max(right_boundary, x0);
                if (i != 0 || bot_color == WHITE_PIECE) {
                    top_boundary = min(top_boundary, y1);
                    bottom_boundary = max(bottom_boundary, y1);
                    left_boundary = min(left_boundary, x1);
                    right_boundary = max(right_boundary, x1);
                }
            }
        }
    }

    // 扩展边界，并生成所有合法棋步
    if (turn_id == 1) {
        if (bot_color == BLACK_PIECE) {
            optimal_moves[0].x = (GRID_SIZE - 1) / 2;
            optimal_moves[0].y = (GRID_SIZE - 1) / 2;
            optimal_moves[1].x = -1;
            optimal_moves[1].y = -1;
            cout << optimal_moves[0].x << ' ' << optimal_moves[0].y << ' ' << optimal_moves[1].x << ' ' << optimal_moves[1].y << endl;
            return 0;
        } else {
            if (top_boundary - 1 >= 0) top_boundary--;
            if (bottom_boundary + 1 < GRID_SIZE) bottom_boundary++;
            if (left_boundary - 1 >= 0) left_boundary--;
            if (right_boundary + 1 < GRID_SIZE) right_boundary++;
        }
    } else {
        if (top_boundary - 2 >= 0) top_boundary -= 2;
        else if (top_boundary - 1 >= 0) top_boundary--;
        if (bottom_boundary + 2 < GRID_SIZE) bottom_boundary += 2;
        else if (bottom_boundary + 1 < GRID_SIZE) bottom_boundary++;
        if (left_boundary - 2 >= 0) left_boundary -= 2;
        else if (left_boundary - 1 >= 0) left_boundary--;
        if (right_boundary + 2 < GRID_SIZE) right_boundary += 2;
        else if (right_boundary + 1 < GRID_SIZE) right_boundary++;
    }
    GenerateLegalMoves(bot_color);

    // 决策
    optimal_moves[0] = legal_moves[0].move;
    optimal_moves[1] = legal_moves[1].move;
    if (turn_id != 1) AlphaBetaSearch(-INFINITY_VALUE, INFINITY_VALUE, 2, bot_color);

    // 输出决策结果
    cout << optimal_moves[0].x << ' ' << optimal_moves[0].y << ' ' << optimal_moves[1].x << ' ' << optimal_moves[1].y << endl;

    return 0;
}
